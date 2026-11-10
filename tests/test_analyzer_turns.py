import unittest
from unittest.mock import Mock

import numpy as np

from chessai.game.analyzer import AnalyzerGame, starting_board_for
from chessai.game.board_moves import apply_move


class AnalyzerTurnsTests(unittest.TestCase):
    def setUp(self):
        self.engine = Mock()
        self.engine.legal_moves.side_effect = lambda board, side: (
            {"a3a4", "b2e2"} if side == "r" else {"b7e7"}
        )
        self.engine.get_best_move.side_effect = lambda board, side, depth: (
            "b2e2" if side == "r" else "b7e7"
        )

    def test_red_player_move_and_computer_response(self):
        board = starting_board_for("r")
        game = AnalyzerGame("r", "medium", board)
        game.prepare(self.engine, 4)
        self.assertEqual(game.next_player, "r")
        with self.assertRaisesRegex(ValueError, "No piece moved"):
            game.end_turn(self.engine, board, 4)
        with self.assertRaisesRegex(ValueError, "Illegal move"):
            game.end_turn(self.engine, apply_move(board, "h7g7"), 4)
        moved = apply_move(board, "i6i5")
        game.end_turn(self.engine, moved, 4)
        self.assertEqual(game.next_player, "b")
        self.assertEqual(game.hint_move, "h2e2")
        game.observe(self.engine, moved, now=0)
        self.assertIsNone(game.warning)
        wrong = apply_move(moved, "h2f2")
        game.observe(self.engine, wrong, now=1)
        game.observe(self.engine, wrong, now=2.9)
        self.assertIsNone(game.warning)
        game.observe(self.engine, wrong, now=3)
        self.assertIn("cannon", game.warning)
        game.observe(self.engine, moved, now=4)
        self.assertIsNone(game.warning)
        game.observe(self.engine, game.expected, now=5)
        self.assertEqual(game.next_player, "r")
        self.assertEqual(game.moves, ["i6i5", "h2e2"])

    def test_black_player_sees_red_move_first(self):
        game = AnalyzerGame("b", "easy", starting_board_for("b"))
        game.prepare(self.engine, 2)
        self.assertEqual(game.next_player, "r")
        self.assertEqual(game.hint_move, "b2e2")
        game.observe(self.engine, game.expected)
        self.assertEqual(game.next_player, "b")
        self.assertEqual(game.moves, ["b2e2"])

    def test_no_legal_move_ends_game(self):
        game = AnalyzerGame("r", "easy", starting_board_for("r"))
        self.engine.legal_moves.side_effect = None
        self.engine.legal_moves.return_value = set()
        game.prepare(self.engine, 2)
        self.assertEqual(game.winner, "b")

    def test_start_positions_have_player_on_top(self):
        self.assertEqual(starting_board_for("r")[0, 4], "rk")
        self.assertEqual(starting_board_for("b")[0, 4], "bk")


if __name__ == "__main__":
    unittest.main()
