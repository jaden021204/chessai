import unittest
import threading
import time
from unittest.mock import Mock

import numpy as np
from fastapi import HTTPException
from pydantic import ValidationError

from chessai import global_data
from chessai.game.analyzer import starting_board_for
from chessai.game.board_moves import apply_move
from chessai.game.pikafish_engine import PikafishEngine
from chessai.routers import xiangqi


class TurnRoutesTests(unittest.TestCase):
    def setUp(self):
        self.saved = (global_data.board_array, global_data.game_state, global_data.chess_engine)
        global_data.board_array = starting_board_for("r")
        global_data.game_state = None
        self.engine = Mock()
        self.engine.legal_moves.side_effect = lambda board, side: (
            {"a3a4"} if side == "r" else {"b7e7"}
        )
        self.engine.get_best_move.return_value = "b7e7"
        global_data.chess_engine = self.engine

    def tearDown(self):
        global_data.board_array, global_data.game_state, global_data.chess_engine = self.saved

    def test_player_move_then_computer_move(self):
        result = xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", position="starting"))
        self.assertEqual(result["next_player"], "r")
        with self.assertRaises(HTTPException) as error:
            xiangqi.play()
        self.assertIn("No piece moved", error.exception.detail)
        global_data.board_array = apply_move(global_data.board_array, "a3a4")
        result = xiangqi.play()
        self.assertEqual(result["next_player"], "b")
        self.assertEqual(result["best_move"], "b7e7")
        global_data.board_array = apply_move(global_data.board_array, "b7e7")
        result = xiangqi.game_snapshot()
        self.assertEqual(result["next_player"], "r")
        self.assertEqual(result["moves"], ["a3a4", "b7e7"])

    def test_rejects_mismatched_start_and_disabled_robot(self):
        global_data.board_array[0, 0] = ""
        with self.assertRaises(HTTPException):
            xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", position="starting"))
        with self.assertRaises(ValidationError):
            xiangqi.NewGameRequest(next_player="r", mode="robot")

    def test_dismissal_updates_the_shared_game_and_ignores_stale_ids(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", time_control="5+5"))
        global_data.game_state.warning = "Please correct the position."
        global_data.game_state.warning_id = "current"
        result = xiangqi.dismiss_warning(xiangqi.DismissWarningRequest(warning_id="old"))
        self.assertEqual(result["warning_id"], "current")
        result = xiangqi.dismiss_warning(xiangqi.DismissWarningRequest(warning_id="current"))
        self.assertIsNone(result["warning"])
        self.assertIsNone(xiangqi.current_game()["warning"])

    def test_board_change_during_analysis_does_not_commit(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", time_control="5+5"))
        original = global_data.game_state
        global_data.board_array = apply_move(global_data.board_array, "a3a4")
        def mutate_board(*args, **kwargs):
            global_data.board_array[1, 0] = "rp"
            return "b7e7"
        self.engine.get_best_move.side_effect = mutate_board
        with self.assertRaises(HTTPException) as error:
            xiangqi.play()
        self.assertEqual(error.exception.status_code, 409)
        self.assertIs(global_data.game_state, original)
        self.assertEqual(global_data.game_state.moves, [])
        self.assertEqual(global_data.game_state.clock.active, "r")
        self.assertLessEqual(global_data.game_state.clock.remaining["r"], 300)

    def test_black_player_cannon_and_engine_orientation(self):
        global_data.board_array = starting_board_for("b")
        self.engine.legal_moves.side_effect = lambda board, side: (
            ({"b2e2"} if board[7][1] == "rc" else {"a0a1"})
            if side == "r" else {"b7e7"}
        )
        self.engine.get_best_move.side_effect = lambda board, side, depth: (
            ("b2e2" if board[7][1] == "rc" else "a0a1")
            if side == "r" else "b7e7"
        )
        result = xiangqi.new_game(xiangqi.NewGameRequest(next_player="b", position="starting"))
        self.assertEqual(result["best_move"], "h7e7")
        global_data.board_array = apply_move(global_data.board_array, "h7e7")
        result = xiangqi.game_snapshot()
        self.assertEqual(result["next_player"], "b")
        result = xiangqi.get_hint()
        self.assertEqual(result["best_move"], "h2e2")
        canonical = self.engine.get_best_move.call_args.args[0]
        self.assertEqual(
            PikafishEngine.board_array_to_fen(canonical, "b"),
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/4C2C1/9/RNBAKABNR b",
        )
        global_data.board_array = apply_move(global_data.board_array, "h2e2")
        result = xiangqi.play()
        self.assertEqual(result["moves"], ["h7e7", "h2e2"])
        self.assertEqual(result["best_move"], "i9i8")

    def test_red_player_cannon_and_engine_orientation(self):
        self.engine.legal_moves.side_effect = lambda board, side: (
            {"b2e2"} if side == "r" else {"b7e7"}
        )
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", position="starting"))
        global_data.board_array = apply_move(global_data.board_array, "b2e2")
        result = xiangqi.play()
        self.assertEqual(result["best_move"], "b7e7")
        canonical = self.engine.get_best_move.call_args.args[0]
        self.assertEqual(
            PikafishEngine.board_array_to_fen(canonical, "b"),
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/4C2C1/9/RNBAKABNR b",
        )
        global_data.board_array = apply_move(global_data.board_array, "b7e7")
        result = xiangqi.game_snapshot()
        self.assertEqual(result["moves"], ["b2e2", "b7e7"])
        self.assertEqual(result["next_player"], "r")

    def test_current_position_preserves_detected_orientation(self):
        for player, physical_move in (("r", "a3a4"), ("b", "i6i5")):
            with self.subTest(player=player):
                global_data.board_array = apply_move(starting_board_for(player), physical_move)
                self.engine.legal_moves.side_effect = lambda board, side: (
                    {"b2e2"} if side == "r" else {"b7e7"}
                )
                self.engine.get_best_move.return_value = "b2e2"
                result = xiangqi.new_game(xiangqi.NewGameRequest(
                    next_player=player, position="current"
                ))
                np.testing.assert_array_equal(result["accepted_board"], global_data.board_array)
                canonical = self.engine.legal_moves.call_args.args[0]
                self.assertEqual(
                    PikafishEngine.board_array_to_fen(canonical, "r"),
                    "rnbakabnr/9/1c5c1/p1p1p1p1p/9/P8/2P1P1P1P/1C5C1/9/RNBAKABNR w",
                )

    def test_clock_times_out_during_engine_analysis_without_blocking_snapshot(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", time_control="5"))
        global_data.board_array = apply_move(global_data.board_array, "a3a4")
        entered = threading.Event()
        release = threading.Event()
        result = []

        def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release engine.")
            return {"a3a4"} if args[1] == "r" else {"b7e7"}

        self.engine.legal_moves.side_effect = delayed

        def move():
            try:
                result.append(xiangqi.play())
            except Exception as exc:
                result.append(exc)

        worker = threading.Thread(target=move)
        worker.start()
        self.assertTrue(entered.wait(2))
        try:
            with global_data.game_lock:
                global_data.game_state.clock.last = time.monotonic() - 301
            snapshot = xiangqi.game_snapshot()
            self.assertEqual(snapshot["winner"], "b")
            self.assertEqual(snapshot["finish_reason"], "timeout")
            self.assertEqual(snapshot["clock"]["remaining"]["r"], 0)
        finally:
            release.set()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result[0]["winner"], "b")
        self.assertEqual(global_data.game_state.moves, [])

    def test_clocks_follow_both_moves_and_apply_increment_once(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", time_control="5+5"))
        with global_data.game_lock:
            global_data.game_state.clock.remaining["r"] = 200
            global_data.game_state.clock.remaining["b"] = 150
        global_data.board_array = apply_move(global_data.board_array, "a3a4")
        result = xiangqi.play()
        self.assertEqual(result["clock"]["active"], "b")
        self.assertAlmostEqual(result["clock"]["remaining"]["r"], 205, delta=0.5)
        global_data.board_array = apply_move(global_data.board_array, "b7e7")
        result = xiangqi.game_snapshot()
        self.assertEqual(result["clock"]["active"], "r")
        self.assertAlmostEqual(result["clock"]["remaining"]["b"], 155, delta=0.5)
        again = xiangqi.game_snapshot()
        self.assertLessEqual(again["clock"]["remaining"]["b"], 155)

    def test_failed_move_does_not_change_clock_side_or_add_increment(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", time_control="5+5"))
        with self.assertRaises(HTTPException):
            xiangqi.play()
        result = xiangqi.game_snapshot()
        self.assertEqual(result["clock"]["active"], "r")
        self.assertLessEqual(result["clock"]["remaining"]["r"], 300)

    def test_black_player_clock_starts_with_com_and_changes_after_placement(self):
        global_data.board_array = starting_board_for("b")
        self.engine.get_best_move.return_value = "b2e2"
        self.engine.legal_moves.side_effect = lambda board, side: (
            {"b2e2"} if side == "r" else {"b7e7"}
        )
        result = xiangqi.new_game(xiangqi.NewGameRequest(
            next_player="b", position="starting", time_control="10+5"
        ))
        self.assertEqual(result["clock"]["active"], "r")
        global_data.board_array = apply_move(global_data.board_array, "h7e7")
        result = xiangqi.game_snapshot()
        self.assertEqual(result["clock"]["active"], "b")
        self.assertAlmostEqual(result["clock"]["remaining"]["r"], 605, delta=0.5)


if __name__ == "__main__":
    unittest.main()
