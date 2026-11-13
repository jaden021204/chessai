import logging
import time
import threading
from itertools import count

import cv2

from chessai import config, global_data
from chessai import profiling

_capture_ids = count(1)


def capture_loop():
    try:
        cap = cv2.VideoCapture(global_data.camera_id)
    except Exception as e:
        logging.error(e)
        return
    try:
        if not cap.isOpened():
            logging.error("Could not open camera %s", global_data.camera_id)
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        global_data.camera_is_running = True
        reported_resolution = False
        while not global_data.camera_shutdown_signal:
            profile_start = time.perf_counter_ns() if profiling.profiler else None
            ret, frame = cap.read()
            profile_end = time.perf_counter_ns() if profile_start is not None else None
            if not ret or frame is None:
                logging.error("Could not read a frame from camera %s", global_data.camera_id)
                break
            if not reported_resolution:
                height, width = frame.shape[:2]
                print(
                    f"Camera resolution: {width}x{height} "
                    f"(requested {config.CAMERA_WIDTH}x{config.CAMERA_HEIGHT})",
                    flush=True,
                )
                if (width, height) != (config.CAMERA_WIDTH, config.CAMERA_HEIGHT):
                    logging.warning("Camera did not provide the requested resolution.")
                reported_resolution = True
            with global_data.frame_lock:
                global_data.original_frame = frame
                if profile_start is not None:
                    global_data.capture_profile = {
                        "capture_id": next(_capture_ids),
                        "capture_start_ns": profile_start,
                        "capture_end_ns": profile_end,
                        "capture_read_ms": (profile_end - profile_start) / 1e6,
                        "capture_width": frame.shape[1],
                        "capture_height": frame.shape[0],
                    }
                else:
                    global_data.capture_profile = None
    finally:
        cap.release()
        global_data.camera_is_running = False


def stop_camera():
    if not global_data.camera_is_running:
        return False
    global_data.camera_shutdown_signal = True
    while global_data.camera_is_running:
        time.sleep(0.01)


def start_camera():
    if global_data.camera_is_running:
        return False
    global_data.camera_shutdown_signal = False
    global_data.camera_thread = threading.Thread(target=capture_loop)
    global_data.camera_thread.start()


def switch_camera(camera_id: int):
    if camera_id not in global_data.working_camera_ports:
        return False
    stop_camera()
    global_data.camera_id = camera_id
    start_camera()
