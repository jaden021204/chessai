import unittest
from unittest.mock import Mock

import numpy as np
from fastapi import HTTPException
from pydantic import ValidationError

from chessai import global_data
from chessai.game.analyzer import starting_board_for
from chessai.game.board_moves import apply_move
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
        global_data.board_array = apply_move(global_data.board_array, "i6i5")
        result = xiangqi.play()
        self.assertEqual(result["next_player"], "b")
        self.assertEqual(result["best_move"], "h2e2")
        global_data.board_array = apply_move(global_data.board_array, "h2e2")
        result = xiangqi.game_snapshot()
        self.assertEqual(result["next_player"], "r")
        self.assertEqual(result["moves"], ["i6i5", "h2e2"])

    def test_rejects_mismatched_start_and_disabled_robot(self):
        global_data.board_array[0, 0] = ""
        with self.assertRaises(HTTPException):
            xiangqi.new_game(xiangqi.NewGameRequest(next_player="r", position="starting"))
        with self.assertRaises(ValidationError):
            xiangqi.NewGameRequest(next_player="r", mode="robot")

    def test_board_change_during_analysis_does_not_commit(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r"))
        original = global_data.game_state
        global_data.board_array = apply_move(global_data.board_array, "i6i5")
        def mutate_board(*args, **kwargs):
            global_data.board_array[1, 0] = "rp"
            return "b7e7"
        self.engine.get_best_move.side_effect = mutate_board
        with self.assertRaises(HTTPException) as error:
            xiangqi.play()
        self.assertEqual(error.exception.status_code, 409)
        self.assertIs(global_data.game_state, original)
        self.assertEqual(global_data.game_state.moves, [])


if __name__ == "__main__":
    unittest.main()
