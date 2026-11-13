import os
import atexit
import argparse
import logging
import pathlib
import threading
import time

import cv2
import imutils

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from chessai.app_info import __appname__, __description__, __version__
from chessai import global_data
from chessai import config, profiling
from chessai.vision.board_aligner import BoardAligner
from chessai.vision.piece_detector import PieceDetector
from chessai.game.chess_engine import ChessEngine
from chessai.visualization import draw_board_canvas
from chessai.utils import list_camera_ports
from chessai.camera_manager import start_camera

aligner = BoardAligner(
    config.REFERENCE_ARUCO_IMAGE_PATH,
    debug=True,
    smooth=False,
)
piece_detector = PieceDetector(
    model_dir=config.PIECE_DETECTION_MODEL_PATH,
    class_names=config.PIECE_DETECTION_CLASS_NAMES,
    score_thr=config.PIECE_DETECTION_CONFIDENCE,
)

engine_path = os.environ.get("ENGINE_PATH", "")
global_data.chess_engine = ChessEngine(engine_path)

def chessai_process(frame, profile=None, capture=None):
    original_frame_viz = frame.copy()
    with profiling.span(profile, "align_ms"):
        _, board_image = aligner.process(frame, visualize=original_frame_viz, profile=profile)
    board_image_viz = board_image.copy()
    board_array = piece_detector.detect(board_image, visualize=board_image_viz, profile=profile)
    with global_data.board_lock:
        global_data.board_array = board_array
        global_data.board_capture_profile = capture

    # Two images on the top
    target_height = 640
    with profiling.span(profile, "debug_render_ms"):
        original_frame_viz = imutils.resize(original_frame_viz, height=target_height)
        board_image_viz = imutils.resize(board_image_viz, height=target_height)
        top_row = cv2.hconcat([board_image_viz, original_frame_viz])
    with global_data.frame_lock:
        global_data.debug_frame = top_row
        global_data.debug_aligned_frame = board_image_viz
        global_data.debug_markers_frame = original_frame_viz

    # Visualize the board
    game = global_data.game_state
    hint = game.hint_move if game else None
    rotate_pieces = bool(game and game.player == "r")
    with profiling.span(profile, "board_render_ms"):
        board_canvas = draw_board_canvas(board_array, hint, rotate_pieces)
        board_canvas = imutils.resize(board_canvas, height=target_height)
    with global_data.frame_lock:
        global_data.visualization_frame = board_canvas

def chessai_process_loop():
    while True:
        with global_data.frame_lock:
            frame = global_data.original_frame
            capture = global_data.capture_profile
        if frame is not None:
            sample = None
            if profiling.profiler and capture:
                with global_data.game_lock:
                    game = global_data.game_state
                    game_active = game is not None and game.winner is None
                if game_active:
                    sample = profiling.profiler.new_frame(capture.copy())
            chessai_process(frame, profile=sample, capture=capture)
            if sample:
                sample.finish()
        else:
            time.sleep(0.05)


def game_clock_loop():
    while True:
        with global_data.game_lock:
            if global_data.game_state is not None:
                global_data.game_state.tick_clock()
        time.sleep(0.1)


def game_observer_loop():
    from chessai.routers.xiangqi import game_snapshot

    while True:
        with global_data.board_lock:
            has_board = global_data.board_array is not None
        with global_data.game_lock:
            has_game = global_data.game_state is not None
        if has_board and has_game:
            try:
                game_snapshot()
            except HTTPException as exc:
                logging.warning("Game observation failed (%s): %s", exc.status_code, exc.detail)
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(
        description=__description__,
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to run the server on",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5678,
        help="Port to run the server on",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )
    parser.add_argument(
        "--data_root",
        default=os.path.abspath(
            os.path.join(os.path.expanduser("~"), "chessai-data")
        ),
    )
    parser.add_argument(
        "--environment",
        default="local",
    )
    parser.add_argument(
        "--run_app",
        default=False,
        action="store_true",
    )
    args = parser.parse_args()

    if args.version:
        print(f"{__appname__} v{__version__}")
        return

    profile_dir = os.environ.get("CHESSAI_PROFILE_DIR")
    if profile_dir:
        profiling.profiler = profiling.Profiler(
            profile_dir,
            frames=int(os.environ.get("CHESSAI_PROFILE_FRAMES", "1000")),
            warmup=int(os.environ.get("CHESSAI_PROFILE_WARMUP", "20")),
        )
        with (profiling.profiler.directory / "metadata.txt").open("a", encoding="utf-8") as file:
            file.write(f"model_dir={piece_detector.model.model_dir}\n"
                       f"model_input={piece_detector.model.input_size}\n"
                       f"ncnn_threads={piece_detector.model.num_threads}\n"
                       f"ncnn_gpu_requested={piece_detector.model.use_gpu}\n"
                       f"aruco_debug={aligner.debug}\n")
        atexit.register(profiling.profiler.close)

    logging.info(f"Starting {__appname__}...")
    logging.info(f"Version: {__version__}")

    logging.info(f"Environment: {args.environment}")
    global_data.environment = args.environment

    logging.info(f"Data root: {args.data_root}")
    global_data.data_root = args.data_root
    pathlib.Path(global_data.data_root).mkdir(parents=True, exist_ok=True)

    # Import these after setting data_root
    from chessai.routers import system_monitor, xiangqi, camera, vision
    from chessai.utils import extract_frontend_dist
    from chessai.database import engine, Base

    logging.info("Extracting frontend distribution...")
    static_folder = os.path.abspath(
        os.path.join(global_data.data_root, "frontend-dist")
    )
    extract_frontend_dist(static_folder)

    logging.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title=__appname__,
        description=__description__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    app.include_router(xiangqi.router)
    app.include_router(system_monitor.router)
    app.include_router(camera.router)
    app.include_router(vision.router)
    app.mount(
        "/", StaticFiles(directory=static_folder, html=True), name="static"
    )

    def run_webapp():
        uvicorn.run(app, host=args.host, port=args.port, workers=1)

    # Start the web server first so the UI is reachable even without a camera
    threading.Thread(target=run_webapp, daemon=True).start()
    threading.Thread(target=game_clock_loop, daemon=True).start()
    threading.Thread(target=game_observer_loop, daemon=True).start()

    # Scan for available camera ports
    logging.info("Scanning for available camera ports...")
    _, global_data.working_camera_ports = list_camera_ports()
    if len(global_data.working_camera_ports) == 0:
        logging.error("No working camera ports found. Please check your camera.")
        while True:  # keep the web server alive
            time.sleep(3600)
    global_data.camera_id = global_data.working_camera_ports[0]

    # Start the chessai process loop
    thread = threading.Thread(target=chessai_process_loop)
    thread.start()

    # Start the capture loop
    start_camera()

if __name__ == "__main__":
    main()
