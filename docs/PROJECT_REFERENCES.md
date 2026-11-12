# Project references for the senior report

These are references for technologies visible in this repository and its
current implementation. They are useful citations, but this list is **not**
a verified record of every website consulted during development. Check your
institution's citation format and record access dates where required.
Update this file when future changes introduce a relevant new source or
technology, identifying whether it is directly used or background reading.

## Core project and hardware

1. **Viet-Anh Nguyen, ChessAI** —
   https://github.com/vietanhdev/chessai. The original Xiangqi board-analysis
   project is the basis for this repository. Its camera, ARUCO alignment,
   board visualization and web architecture are the starting point that was
   adapted for the Pi and the new detector.
2. **Raspberry Pi Ltd., Raspberry Pi 5 documentation** —
   https://www.raspberrypi.com/documentation/computers/raspberry-pi.html.
   The Pi is the target computer running camera capture, recognition, the
   server and Pikafish; it is not itself a recognition algorithm.

## Vision and model inference

3. **OpenCV, ArUco marker detection** —
   https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html.
   `chessai/vision/board_aligner.py` detects markers and uses their positions
   to align the camera image. Perspective correction turns an angled board
   image into a standardized board view before detection.
4. **Garrido-Jurado et al., “Automatic generation and detection of highly
   reliable fiducial markers under occlusion,” Pattern Recognition, 2014** —
   https://doi.org/10.1016/j.patcog.2014.01.005. This is a research background
   reference for ArUco-style markers; cite it for the underlying technique,
   not as evidence that the paper itself was directly used to write code.
5. **Ultralytics, YOLO26** —
   https://docs.ultralytics.com/models/yolo26/. The supplied
   `data/my_model_ncnn_model/metadata.yaml` identifies the trained model as
   YOLO26s with 14 piece/color classes and 640×640 input. The project uses
   that model for piece recognition, not the original ChessAI YOLOX detector.
   Verify your training procedure, dataset and model metrics separately.
6. **Tencent, ncnn** — https://github.com/Tencent/ncnn. This is the inference
   runtime used to run the exported neural network on the Pi. See
   `chessai/dnn/ncnn_runtime.py` and `chessai/dnn/yolo26s_ncnn.py` for loading,
   preprocessing and decoding.
7. **NumPy** — https://numpy.org/. It supplies arrays and numerical operations
   used for images, model output and the 10×9 board representation.

## Game analysis and interfaces

8. **Pikafish** — https://github.com/official-pikafish/Pikafish. A Xiangqi
   engine derived from Stockfish; it supplies legal moves and suggestions.
   `chessai/game/pikafish_engine.py` sends the position and commands to the
   separately installed binary. The user tested the Pi binary's `go perft 1`
   output. Search depth presets are not calibrated Elo ratings.
9. **FastAPI** — https://fastapi.tiangolo.com/. The Pi backend exposes game,
   camera and image endpoints; see `chessai/routers/`. The web UI and Android
   preview use these shared endpoints instead of separate board states.
10. **Next.js and React** — https://nextjs.org/ and https://react.dev/.
    These provide the existing browser interface in `frontend/`; the
    upstream README also credits **shadcn/ui**, https://ui.shadcn.com/, for
    UI components.
11. **Flutter** — https://flutter.dev/. The Android preview in `android_app/`
    uses Flutter for its interface and communicates with the Pi over the
    local network. Its source was added separately from the existing web UI;
    verify its actual build and device-test results before claiming success.

## Timers and remote control

12. **Python `time.monotonic` documentation** —
    https://docs.python.org/3/library/time.html#time.monotonic. This explains
    a clock that is not affected by wall-clock adjustments. The Pi's
    `chessai/game/clock.py` uses it to measure elapsed time for both sides;
    `chessai/routers/xiangqi.py` shares clock state with the clients.
13. **systemd user services and `systemctl`** —
    https://www.freedesktop.org/software/systemd/man/latest/systemctl.html
    and https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html.
    systemd manages services on Linux. The optional controller uses
    `systemctl --user` in `chessai/remote_control.py` to start and stop only
    the configured ChessAI service; it cannot switch on a powered-off Pi.
    The installation examples are in `android_app/README.md`.
14. **Python `http.server`, `subprocess`, and `hmac` documentation** —
    https://docs.python.org/3/library/http.server.html,
    https://docs.python.org/3/library/subprocess.html, and
    https://docs.python.org/3/library/hmac.html. The controller uses these
    standard-library modules for its HTTP endpoints, systemd command calls,
    and token comparison. Python explicitly warns that `http.server` is not
    recommended for production. The controller's HTTP is unencrypted and the
    main game API is unauthenticated, so the current design is for a trusted
    local network only, not public internet deployment.
15. **Dart `HttpClientRequest`** —
    https://api.dart.dev/dart-io/HttpClientRequest-class.html. The Android
    client's `PiApi` in `android_app/lib/main.dart` sends game and controller
    requests. The client sets the authorization and content-type headers before
    writing a POST body, so the controller can receive the token.
16. **Python `time.sleep`** —
    https://docs.python.org/3/library/time.html#time.sleep. The camera and
    processing loops in `chessai/camera_manager.py` and `chessai/app.py`
    briefly sleep when waiting for shutdown or a first frame, avoiding
    continuous CPU polling in those specific conditions.

## Earlier components and unknowns

- The original ChessAI README credits **YOLOX**
  (https://github.com/Megvii-BaseDetection/YOLOX) and **godogpaw**
  (https://github.com/hmgle/godogpaw). They describe the original project's
  detector and engine, not the currently configured YOLO26s and Pikafish.
  Mention them when discussing the project's history, not as the active
  model or engine.
- The model metadata names a training data path, but it does not establish a
  dataset author, URL, license, split, or training metrics. Ask the model
  trainer for those details before citing the dataset or reporting accuracy.
- The supplied font and texture were not committed to the Android preview:
  their licensing was not established. Cite and verify their original
  creators and licenses if you add them.
- If your school requires disclosure of AI-assisted coding, describe the
  assistance and cite the tool according to your school's guidance.
