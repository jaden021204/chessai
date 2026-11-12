import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from chessai import camera_manager, config, global_data


class CameraTests(unittest.TestCase):
    def test_capture_requests_size_and_reports_actual_frame(self):
        camera = MagicMock()
        camera.isOpened.return_value = True
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        camera.read.side_effect = [(True, frame), (False, None)]
        global_data.camera_shutdown_signal = False

        with patch.object(camera_manager.cv2, "VideoCapture", return_value=camera):
            with self.assertLogs(level="WARNING") as logs:
                camera_manager.capture_loop()

        camera.set.assert_any_call(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        camera.set.assert_any_call(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self.assertTrue(any("did not provide" in line for line in logs.output))
        self.assertIs(global_data.original_frame, frame)
        self.assertFalse(global_data.camera_is_running)
        camera.release.assert_called_once()

    def test_stop_waits_without_spinning(self):
        global_data.camera_is_running = True
        global_data.camera_shutdown_signal = False

        def finish_capture(_):
            self.assertTrue(global_data.camera_shutdown_signal)
            global_data.camera_is_running = False

        try:
            with patch.object(camera_manager.time, "sleep", side_effect=finish_capture) as sleep:
                camera_manager.stop_camera()
            sleep.assert_called_once_with(0.01)
        finally:
            global_data.camera_is_running = False
            global_data.camera_shutdown_signal = False


if __name__ == "__main__":
    unittest.main()
