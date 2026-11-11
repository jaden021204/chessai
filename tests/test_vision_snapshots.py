import asyncio
import unittest

import cv2
import numpy as np

from chessai import config, global_data
from chessai.routers import vision


class VisionSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.saved = (
            global_data.original_frame,
            global_data.debug_aligned_frame,
            global_data.debug_markers_frame,
        )

    def tearDown(self):
        (global_data.original_frame, global_data.debug_aligned_frame,
         global_data.debug_markers_frame) = self.saved

    def test_each_endpoint_returns_its_own_frame(self):
        global_data.original_frame = np.full((20, 30, 3), 30, dtype=np.uint8)
        global_data.debug_aligned_frame = np.full((20, 30, 3), 100, dtype=np.uint8)
        global_data.debug_markers_frame = np.full((20, 30, 3), 200, dtype=np.uint8)
        for endpoint, expected in (
            (vision.original_snapshot, 30),
            (vision.debug_aligned_frame, 100),
            (vision.debug_markers_frame, 200),
        ):
            with self.subTest(endpoint=endpoint.__name__):
                response = asyncio.run(endpoint())
                self.assertEqual(response.media_type, "image/jpeg")
                self.assertEqual(response.headers["cache-control"], "no-store")
                decoded = cv2.imdecode(np.frombuffer(response.body, np.uint8), cv2.IMREAD_COLOR)
                self.assertEqual(decoded.shape, (20, 30, 3))
                self.assertLess(abs(float(decoded.mean()) - expected), 3)

    def test_missing_frame_uses_existing_placeholder(self):
        global_data.debug_aligned_frame = None
        response = asyncio.run(vision.debug_aligned_frame())
        decoded = cv2.imdecode(np.frombuffer(response.body, np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape, config.DEFAULT_VISUALIZATION_FRAME.shape)


if __name__ == "__main__":
    unittest.main()
