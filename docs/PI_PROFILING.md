# Measuring ChessAI on the Raspberry Pi

These measurements must be collected on your own Pi with its real camera,
physical board and screen. The development environment cannot measure your Pi.
Profiling is **off by default** and adds timing, CSV writes, and roughly
one-second resource samples; these add overhead. Compare an ordinary run with
the profiled run if you need to quantify that overhead.

## 1. Prepare

1. Update `android-flutter-preview` on the Pi. First run `git status` in
   `~/chessai`; do not overwrite local edits. Resolve any Git warning before
   pulling. Make sure the game, camera and Pikafish work normally.
2. Keep the phone or browser connected, and use your usual board, camera
   resolution, lighting, cooling and difficulty. Record those conditions and
   the Pi OS, power supply, model and engine versions in your report.
3. This procedure restarts the ChessAI game service and **ends its current
   game**. The separate remote controller remains running. The commands below
   assume the `chessai.service` described in `android_app/README.md` is set up.

In a terminal **on the Pi**:

```bash
cd ~/chessai
source .venv/bin/activate
mkdir -p ~/chessai-profiles
PROFILE_DIR="$HOME/chessai-profiles/$(date +%Y%m%d-%H%M%S)"
echo "$PROFILE_DIR"
systemctl --user stop chessai.service
systemctl --user set-environment "CHESSAI_PROFILE_DIR=$PROFILE_DIR"
systemctl --user start chessai.service
systemctl --user unset-environment CHESSAI_PROFILE_DIR
systemctl --user status chessai.service --no-pager
```

`PROFILE_DIR` is a shell variable: keep this terminal open for the commands
below. Write down its printed path in case the terminal closes. Each run needs
a **new directory**; existing directories are never overwritten. The service
inherits its existing `ENGINE_PATH`; its service file need not be edited.
The controller can still operate the service, but do not restart the game
service during this run: the one-time profiling setting has been removed.

If you normally run ChessAI manually instead of the service, stop any other
ChessAI instance first. In the Pi terminal, use the same `cd`, activation,
`mkdir`, and `PROFILE_DIR` commands above, then start with your actual engine
path, for example:

```bash
CHESSAI_PROFILE_DIR="$PROFILE_DIR" ENGINE_PATH="/full/path/to/pikafish" \
  python -m chessai.app --run_app
```

Leave that process running and use a second terminal for the remaining
commands; set `PROFILE_DIR` there to the exact path printed by the first
terminal.

## 2. Record gameplay

1. Start an Analyzer game in the web UI or Android app. Play normally, making
   moves and using hints so Pikafish actually handles requests.
2. The profiler skips 20 distinct processed camera captures for warm-up, then
   saves **1,000 distinct processed captures while a game is active**. A game
   ending pauses frame collection; starting another continues it. It can
   reprocess the same camera capture during normal operation, but records that
   capture only once. If processing is slower than the camera, intermediate
   captures are skipped.
3. In the Pi terminal, check progress:

   ```bash
   wc -l "$PROFILE_DIR/frames.csv"
   ```

   A completed file has **1001 lines**, including its header. If it does not
   grow, check the game is active, camera works and the application logs
   (`journalctl --user -u chessai.service -n 50 --no-pager`). Engine and
   resource logging continue after 1,000 frames until ChessAI stops.

`frames.csv` records the associated camera capture, actual capture dimensions,
individual processing stages, whether homography updating was attempted and
whether a warp was applied. `engine.csv` records each legal-move or search
event separately, including errors; `resources.csv` records CPU, system
memory, swap, process-tree RSS, temperature, clock and throttle flags.
`metadata.txt` records the run settings. Records are flushed as they are
written; an interrupted run may be incomplete.

## 3. Optional: repeatable detected-board recovery trials

This estimates **keypress-to-detected-board API response**, not the physical
hand-removal-to-screen time. Human reaction time, polling and the camera's
internal buffering make it unsuitable to prove the 300 ms screen target.
The trial program runs **on the same Pi**, using the same clock as the server.
Keep profiling enabled, use a steady board position, and don't make moves or
change its orientation during the trials.

1. With the hand absent and all pieces correctly detected, save a candidate
   reference. This command refuses to overwrite an existing reference:

   ```bash
   python -c 'import json,sys,urllib.request; d=json.load(urllib.request.urlopen("http://127.0.0.1:5678/api/vision/profile_board")); f=open(sys.argv[1],"x"); json.dump(d["board"],f,indent=2); f.close()' "$PROFILE_DIR/reference-board.json"
   cat "$PROFILE_DIR/reference-board.json"
   ```

2. **Independently verify every one of the 90 entries** against the physical
   board in the same orientation as Debug View. `""` is empty; `b` and `r`
   mean black and red, followed by `k` king, `a` advisor, `b` elephant, `n`
   horse, `r` rook, `c` cannon or `p` pawn. The saved detected array is only a
   candidate, not independent ground truth until you verify it. Fix
   `"$PROFILE_DIR/reference-board.json"` with a text editor if needed, or
   correct detection before proceeding.
3. Run 10 trials:

   ```bash
   python tools/recovery_probe.py --reference "$PROFILE_DIR/reference-board.json" \
     --output "$PROFILE_DIR/recovery.csv" --trials 10
   ```

   For each trial cover some pieces, wait for the displayed board to change,
   and press Enter. If the detector has not changed, the trial is marked
   `not_occluded`. Then remove your hand and immediately press Enter. The
   program waits up to 10 seconds for a complete 90-cell match from a capture
   whose **capture call started after the keypress**. A match, timeout or
   undetected occlusion is written to the CSV. Buffered camera frames may
   nonetheless be older than that capture call. API polling and screen refresh
   are different; this experiment adds load and does not determine screen
   latency. Never omit failed trials when reporting results.

For the actual hand-to-screen metric, record the board, hand and actual
display together with an independent high-frame-rate camera. Confirm the
display really changes during occlusion and returns to the independently
verified board; record both successful and failed trials. Identify the last
video frame where the hand still blocks the board and the first frame showing
the fully correct screen; use video timestamps and report frame-interval
uncertainty and any rolling-shutter or variable-frame-rate limitations.
At 240 recorded frames per second, one frame interval is about 4.17 ms.
This method measures the whole visible chain, including the web/Android
refresh interval (currently approximately one second), rather than assuming
the Pi-side canvas is already on screen.

## 4. Stop and summarize

After gameplay and any recovery trials, stop the profiling run and generate a
report. Stopping ChessAI ends the game. With the service:

```bash
systemctl --user stop chessai.service
python tools/profile_report.py "$PROFILE_DIR" > "$PROFILE_DIR/report.json"
cat "$PROFILE_DIR/report.json"
systemctl --user start chessai.service
```

The last command starts the normal, unprofiled service. For a manually
started application, stop it in its terminal instead and run the report
command in the other terminal. CSV output is already flushed.

The report includes counts, means, medians, 95th percentiles and maxima.
`complete` is false if fewer than 1,000 frames were recorded. If no engine
events occurred, there is no engine result. Missing firmware or resource
data are reported as inconclusive; check the CSV `errors` field and logs.
Sensor samples are restricted to the first recorded capture through the last
recorded canvas publication.

## 5. Interpret the numbers correctly

- **Capture:** `capture_read_ms` is the OpenCV read call, including driver
  wait and decoding/buffering; it is not isolated USB transfer time. Camera
  capture and processing overlap on separate threads.
- **Alignment:** `align_ms` covers ArUco detection, marker drawing and the
  warp. The existing code attempts to update homography about once per
  second, not on every frame; the attempt and warp counts are in the report.
- **YOLO:** `ncnn_extract_ms` is wall time around CPU-configured NCNN
  extraction, the closest available forward-pass measurement; it includes
  runtime overhead and scheduling. Preprocessing, input setup, output copying,
  postprocessing and overlays are listed separately. It is not a measurement
  of CPU cycles or pure mathematical computation.
- **Grid:** `grid_snap_ms` includes the mapping to the 90 positions and
  reshaping the board. Grid drawing is separate.
- **Pikafish:** `perft1` is legal-move generation, not all validation work.
  `search` is best-move calculation. The total includes validation, process
  startup/shutdown and lock wait; the UCI interval covers command to response.
  These happen per event, **not once per frame**. Both statistics include all
  logged events during the run, including game preparation.
- **GUI:** `board_render_ms` is creating and resizing the Pi-side image, not
  transmitting it, decoding it on Android, or showing it on a screen.
  `capture_start_to_canvas_ms` ends when that image is published in server
  memory. It excludes physical exposure, buffered-frame age, network, client
  refresh and screen presentation.
- **Pie chart:** `processing_pie_mean_ms` partitions mean **processing-thread
  wall time** into non-overlapping measured sections plus other processing.
  Use this only for that explicitly labeled pie chart. Do not add capture
  time, end-to-end time, or engine-event time to it; those overlap or have
  different frequencies. Determine the largest measured share instead of
  assuming YOLO is the bottleneck.
- **CPU, memory and temperature:** `system_used_gib` is total RAM minus
  available RAM, not just ChessAI's memory; process-tree RSS can count shared
  memory more than once. The 14 GB comparison uses **14,000,000,000 bytes**,
  about 13.04 GiB. Inspect swap use over time as well. Threshold messages
  describe only samples and cannot exclude short-lived peaks.
- **Throttling:** `get_throttled` current bits 1–3 indicate frequency capping,
  throttling or a soft temperature limit. Bits 16–19 are historical since
  boot and may predate the run; bit 0 and bit 16 indicate current and past
  undervoltage. Check the raw flags and investigate any active flag. Missing
  data or too few samples is inconclusive; a clock change alone can be normal
  power management. Even normal samples cannot rule out every transient.

Keep the raw CSVs, report and environmental conditions together. No result
from this tool proves all temperatures were under 80°C or that all physical
screen recovery times were under 300 ms.
