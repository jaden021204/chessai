import unittest

import numpy as np

from chessai.game.board_moves import (
    START_BOARD, apply_move, canonical_board, find_move, flip_move,
)


class BoardMovesTests(unittest.TestCase):
    def test_rotation_matches_camera_orientation(self):
        red_at_top = np.rot90(START_BOARD, 2)
        np.testing.assert_array_equal(canonical_board(red_at_top, "b"), START_BOARD)
        np.testing.assert_array_equal(canonical_board(START_BOARD, "r"), START_BOARD)
        np.testing.assert_array_equal(red_at_top, np.rot90(START_BOARD, 2))

    def test_every_move_round_trips(self):
        squares = [f"{file}{rank}" for file in "abcdefghi" for rank in range(10)]
        for origin in squares:
            for target in squares:
                move = origin + target
                self.assertEqual(flip_move(flip_move(move)), move)
        self.assertEqual(flip_move("a0i9"), "i9a0")
        with self.assertRaises(ValueError):
            flip_move("a10i9")

    def test_normal_move_and_capture(self):
        board = START_BOARD.copy()
        moved = apply_move(board, "a3a4")
        self.assertEqual(find_move(board, moved, "r"), "a3a4")
        captured = apply_move(board, "b2b9")
        self.assertEqual(find_move(board, captured, "r"), "b2b9")
        np.testing.assert_array_equal(board, START_BOARD)

    def test_incomplete_or_wrong_side_moves_are_rejected(self):
        board = START_BOARD.copy()
        with self.assertRaisesRegex(ValueError, "No piece moved"):
            find_move(board, board.copy(), "r")
        with self.assertRaisesRegex(ValueError, "other side"):
            find_move(board, apply_move(board, "a6a5"), "r")
        changed = board.copy()
        changed[0, 0] = ""
        changed[9, 0] = ""
        changed[3, 0] = ""
        with self.assertRaisesRegex(ValueError, "More than one piece"):
            find_move(board, changed, "r")


if __name__ == "__main__":
    unittest.main()
