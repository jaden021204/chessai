# Running ChessAI on a Raspberry Pi 5

Tested pieces: `requirements.txt` install, NCNN detector, and web server start were verified on a Linux x86 machine. **Not yet verified on a real Pi, with a real camera, or with Pikafish** (the Pikafish adapter is not implemented yet, so the Hint button will not work).

You need: Raspberry Pi 5 with 64-bit Raspberry Pi OS (Bookworm), internet, a **USB webcam**, and a keyboard/monitor or SSH.

## 1. Install system tools (once)

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip nodejs npm v4l-utils
```

Check versions: `python3 --version` (3.11+), `node --version` (must be 18 or newer).

## 2. Get the code

```bash
cd ~
git clone https://github.com/jaden021204/chessai.git
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

Your webcam should appear as `/dev/video0` (or similar). The Pi's ribbon-cable camera does **not** work with this code; use a USB webcam.

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

If the page loads but the camera list is empty, the camera was not found (step 5).

## Troubleshooting

- `No module named cv2`/`ncnn`: the virtual environment is not active (step 3).
- `frontend-dist not found` message on the page: redo step 4, then `pip install -e . --no-deps`.
- Black/no camera image: unplug/replug the webcam, press **Reset Camera**.
