import unittest
from unittest.mock import Mock, patch

import numpy as np
from fastapi import HTTPException

from chessai import global_data
from chessai.routers import xiangqi
from test_pikafish_engine import START_BOARD


class AnalyzerDifficultyTests(unittest.TestCase):
    def setUp(self):
        self.board = np.rot90(np.array(START_BOARD, dtype=object), 2).copy()
        self.engine = Mock()
        self.engine.legal_moves.return_value = {"b2e2"}
        self.engine.get_best_move.return_value = "b2e2"
        self.saved = (global_data.board_array, global_data.game_state,
                      global_data.prev_game_state, global_data.chess_engine)
        global_data.board_array = self.board
        global_data.game_state = None
        global_data.chess_engine = self.engine

    def tearDown(self):
        (global_data.board_array, global_data.game_state,
         global_data.prev_game_state, global_data.chess_engine) = self.saved

    def test_selected_difficulty_reaches_engine(self):
        for difficulty, depth in xiangqi.DIFFICULTY_DEPTHS.items():
            request = xiangqi.NewGameRequest(next_player="r", difficulty=difficulty)
            xiangqi.new_game(request)
            result = xiangqi.get_hint()
            self.assertEqual(result["depth"], depth)
            self.engine.get_best_move.assert_called_with(unittest.mock.ANY, "r", depth=depth)
            self.assertEqual(global_data.game_state.hint_move, "h7e7")

    def test_board_change_rejects_stale_hint(self):
        xiangqi.new_game(xiangqi.NewGameRequest(next_player="r"))
        def move_during_analysis(*args, **kwargs):
            global_data.board_array[0, 0] = ""
            return "b2e2"
        self.engine.get_best_move.side_effect = move_during_analysis
        with self.assertRaises(HTTPException) as error:
            xiangqi.get_hint()
        self.assertEqual(error.exception.status_code, 409)
        self.assertIsNone(global_data.game_state.hint_move)


if __name__ == "__main__":
    unittest.main()
