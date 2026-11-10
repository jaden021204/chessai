import unittest
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

    def test_board_change_during_analysis_does_not_commit(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r"))
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


if __name__ == "__main__":
    unittest.main()
