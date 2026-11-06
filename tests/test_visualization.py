import unittest
from unittest.mock import patch

import numpy as np

from chessai import config, visualization


class VisualizationTests(unittest.TestCase):
    def test_grid_centers_match_board_image(self):
        image = visualization.ref_board_image
        self.assertEqual(len(config.VISUALIZATION_COLUMN_X), 9)
        self.assertEqual(len(config.VISUALIZATION_ROW_Y), 10)
        for y in config.VISUALIZATION_ROW_Y:
            for x in config.VISUALIZATION_COLUMN_X:
                with self.subTest(x=x, y=y):
                    self.assertLess(int(image[y, x].max()), 80)

    def test_all_pieces_are_centered_and_unclipped(self):
        board = np.full((10, 9), "bp", dtype=object)
        placements = []

        def record_overlay(background, image, x, y):
            placements.append((x, y, image.shape[1], image.shape[0]))
            return background

        with patch.object(visualization, "overlay", side_effect=record_overlay):
            result = visualization.draw_board_canvas(board)

        self.assertEqual(len(placements), 90)
        self.assertEqual(placements[0][2:], (101, 101))
        padding_x = placements[0][0] + 50 - config.VISUALIZATION_COLUMN_X[0]
        padding_y = placements[0][1] + 50 - config.VISUALIZATION_ROW_Y[0]
        for i, (x, y, width, height) in enumerate(placements):
            row, col = divmod(i, 9)
            self.assertEqual(x + width // 2, config.VISUALIZATION_COLUMN_X[col] + padding_x)
            self.assertEqual(y + height // 2, config.VISUALIZATION_ROW_Y[row] + padding_y)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + width, result.shape[1])
            self.assertLessEqual(y + height, result.shape[0])

    def test_hint_uses_same_centers_as_pieces(self):
        board = np.full((10, 9), "", dtype=object)
        with patch.object(visualization.cv2, "arrowedLine", wraps=visualization.cv2.arrowedLine) as arrow:
            visualization.draw_board_canvas(board, "a9i0")
        start, end = arrow.call_args.args[1:3]
        self.assertEqual(end[0] - start[0], config.VISUALIZATION_COLUMN_X[-1] - config.VISUALIZATION_COLUMN_X[0])
        self.assertEqual(end[1] - start[1], config.VISUALIZATION_ROW_Y[-1] - config.VISUALIZATION_ROW_Y[0])


if __name__ == "__main__":
    unittest.main()
