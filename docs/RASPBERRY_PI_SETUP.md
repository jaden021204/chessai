# Running ChessAI on a Raspberry Pi 5

Tested pieces: `requirements.txt` install, NCNN detector, and web server start were verified on a Linux x86 machine. **Not yet verified on a real Pi, with a real camera, or with Pikafish** (the Pikafish adapter is not implemented yet, so the Hint button will not work).

You need: Raspberry Pi 5 with 64-bit Raspberry Pi OS (Bookworm), internet, a camera available to OpenCV, and a keyboard/monitor or SSH.

## 1. Install system tools (once)

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip nodejs npm v4l-utils
```

Check versions: `python3 --version` (3.11+), `node --version` (must be 18 or newer).

## 2. Get the code

```bash
cd ~
git clone -b pi5-setup https://github.com/jaden021204/chessai.git
cd chessai
```

## 3. Create a Python environment and install libraries

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e . --no-deps
```

Run `source .venv/bin/activate` again in every new terminal (your prompt shows `(.venv)`).

## 4. Build the web page (once, and after any frontend change)

```bash
bash build_frontend.sh
```

This takes several minutes on a Pi and needs internet (it downloads fonts).

## 5. Check the camera

```bash
v4l2-ctl --list-devices
```

Your camera should appear as `/dev/video0` (or similar). USB webcams are one
option; compatibility with a ribbon-cable Pi camera has not been verified.

The app requests 1280x960 from the camera. The terminal prints the resolution
actually received when capture starts. Cameras may use a different size if
they do not support the request. To list supported webcam formats, run
`v4l2-ctl -d /dev/video0 --list-formats-ext` (replace `/dev/video0` with
your device). In `chessai/config.py`, change `CAMERA_WIDTH` and
`CAMERA_HEIGHT` to a supported pair, then restart the app. A larger capture
can slow the Pi, and the detector still resizes the aligned board to the
model's required 640x640 input.

If classifications remain unreliable, try increasing
`PIECE_DETECTION_CONFIDENCE` in `chessai/config.py` from 0.35 to 0.45, then
restart the app. A higher threshold hides more low-confidence detections; it
does not correct a confidently incorrect class and may hide real pieces.

## 6. Test the detector without the camera

```bash
python tools/test_piece_detector.py --image test_board.png --output result.png
```

Expect a printed 10x9 grid and "Detected occupied squares: 8".

## 7. Run the app

```bash
python -m chessai.app --run_app
```

Open `http://localhost:5678` on the Pi, or `http://<pi-ip>:5678` from a phone/PC on the same network. Find the IP with `hostname -I`. Stop with Ctrl+C.

To select your existing Pikafish binary path, start the app with:

```bash
ENGINE_PATH="/full/path/to/your/pikafish" python -m chessai.app --run_app
```

Replace the example path with the actual executable path. The path is read in
`chessai/app.py`; it overrides the old godogpaw default. **This does not make
hints work yet:** `chessai/game/pikafish_engine.py` is still a stub and
`chessai/game/chess_engine.py` needs to be reconciled with it. The exact
binary's protocol and output need to be verified before that integration.

For the displayed board only, `chessai/config.py` contains
`VISUALIZATION_PIECE_SCALE` (1.5 means 50% larger than the original images),
`VISUALIZATION_OFFSET_X` (positive moves right) and
`VISUALIZATION_OFFSET_Y` (positive moves down). Change these and restart.
`VISUALIZATION_COLUMN_X` and `VISUALIZATION_ROW_Y` specify the intersections
on `data/board.png`. These settings do not alter camera alignment or piece
detection.

If the page loads but the camera list is empty, the camera was not found (step 5).

## Troubleshooting

- `No module named cv2`/`ncnn`: the virtual environment is not active (step 3).
- `frontend-dist not found` message on the page: redo step 4, then `pip install -e . --no-deps`.
- Black/no camera image: unplug/replug the webcam, press **Reset Camera**.
