import csv
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi import HTTPException

from chessai import global_data, profiling
from chessai.game.pikafish_engine import EngineError, PikafishEngine
from chessai.routers import vision
from tools import recovery_probe


def capture(identifier):
    now = time.perf_counter_ns()
    return {"capture_id": identifier, "capture_start_ns": now - 1000,
            "capture_end_ns": now, "capture_read_ms": 0.001,
            "capture_width": 640, "capture_height": 480}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


class ProfilingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "run"
        self.original_profiler = profiling.profiler
        self.addCleanup(setattr, profiling, "profiler", self.original_profiler)

    def test_warmup_unique_frames_and_incomplete_report(self):
        run = profiling.Profiler(self.directory, frames=2, warmup=1)
        self.addCleanup(run.close)
        self.assertIsNone(run.new_frame(capture(1)))
        self.assertIsNone(run.new_frame(capture(1)))
        frame = run.new_frame(capture(2))
        with profiling.span(frame, "align_ms"):
            pass
        frame.finish()
        self.assertIsNone(run.new_frame(capture(2)))
        rows = read_csv(self.directory / "frames.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["capture_id"], "2")
        self.assertGreaterEqual(float(rows[0]["align_ms"]), 0)
        output = subprocess.check_output(
            [sys.executable, "tools/profile_report.py", str(self.directory)], text=True
        )
        report = json.loads(output)
        self.assertFalse(report["complete"])
        self.assertEqual(report["recorded_distinct_frames"], 1)
        self.assertIn("inconclusive", report["sampled_temperature_80_c"])
        run.new_frame(capture(3)).finish()
        self.assertIsNone(run.new_frame(capture(4)))
        self.assertEqual(len(read_csv(self.directory / "frames.csv")), 2)

    def test_output_directory_must_be_new(self):
        self.directory.mkdir()
        with self.assertRaises(FileExistsError):
            profiling.Profiler(self.directory)

    def test_one_thousand_frames_and_sampled_thresholds(self):
        run = profiling.Profiler(self.directory, frames=1000, warmup=0)
        self.addCleanup(run.close)
        first = None
        last = None
        fields = ("align_ms", "preprocess_ms", "ncnn_input_ms", "ncnn_extract_ms",
                  "ncnn_output_copy_ms", "postprocess_ms", "detection_overlay_ms",
                  "grid_snap_ms", "grid_overlay_ms", "debug_render_ms", "board_render_ms")
        for identifier in range(1, 1001):
            source = capture(identifier)
            first = source["capture_start_ns"] if first is None else first
            frame = run.new_frame(source)
            frame.times.update({name: 0 for name in fields})
            frame.times.update(homography_attempted=0, warp_applied=1)
            last = frame.start_ns
            frame.finish()
        run.write("resources", {"timestamp_ns": first + 1, "system_used_gib": 1,
                                "temperature_c": 79, "throttled_hex": "0x0"})
        run.write("resources", {"timestamp_ns": last - 1, "system_used_gib": 14,
                                "temperature_c": 80, "throttled_hex": "0x4"})
        report = json.loads(subprocess.check_output(
            [sys.executable, "tools/profile_report.py", str(self.directory)], text=True
        ))
        self.assertTrue(report["complete"])
        self.assertEqual(report["frames_ms"]["ncnn_extract_ms"]["count"], 1000)
        self.assertEqual(report["warp_applied_frames"], 1000)
        self.assertIn("exceeded", report["sampled_memory_14_decimal_gb"])
        self.assertIn("exceeded", report["sampled_temperature_80_c"])
        self.assertEqual(report["current_frequency_cap_or_throttling_samples"], 1)

    def test_engine_success_failure_and_disabled(self):
        environment = patch.dict(os.environ, {"FAKE_ENGINE_LOG": str(Path(self.temp.name) / "engine.log")})
        environment.start()
        self.addCleanup(environment.stop)
        script = os.path.abspath("tests/fake_pikafish.py")
        engine = PikafishEngine(script, startup_timeout=2, search_timeout=5)
        board = [[""] * 9 for _ in range(10)]
        board[0][4], board[9][4], board[6][4] = "bk", "rk", "rp"
        profiling.profiler = None
        self.assertEqual(engine.get_best_move(board, "r"), "b2e2")
        run = profiling.Profiler(self.directory, frames=1, warmup=0)
        self.addCleanup(run.close)
        profiling.profiler = run
        self.assertEqual(engine.legal_moves(board, "r"), {"a3a4", "b2e2"})
        with patch.dict(os.environ, {"FAKE_ENGINE_ERROR": "1"}):
            with self.assertRaises(EngineError):
                engine.get_best_move(board, "r", depth=2)
        rows = read_csv(self.directory / "engine.csv")
        self.assertEqual([row["outcome"] for row in rows], ["ok", "error"])
        self.assertEqual(rows[0]["operation"], "perft1")
        self.assertGreater(float(rows[0]["uci_command_ms"]), 0)
        self.assertEqual(rows[1]["depth"], "2")
        self.assertEqual(rows[1]["uci_command_ms"], "")

    def test_profile_board_is_gated_and_returns_source_capture(self):
        old_board, old_capture = global_data.board_array, global_data.board_capture_profile
        self.addCleanup(setattr, global_data, "board_array", old_board)
        self.addCleanup(setattr, global_data, "board_capture_profile", old_capture)
        global_data.board_array = np.full((10, 9), "", dtype=object)
        global_data.board_capture_profile = capture(42)
        profiling.profiler = None
        with self.assertRaises(HTTPException) as error:
            vision.profile_board()
        self.assertEqual(error.exception.status_code, 404)
        profiling.profiler = object()
        result = vision.profile_board()
        self.assertEqual(result["capture_id"], 42)
        self.assertEqual(result["board"], [[""] * 9 for _ in range(10)])

    def test_recovery_requires_a_fresh_post_keypress_capture(self):
        reference = [[""] * 9 for _ in range(10)]
        covered = [[""] * 9 for _ in range(10)]
        covered[0][0] = "bp"
        reference_path = Path(self.temp.name) / "reference.json"
        output_path = Path(self.temp.name) / "recovery.csv"
        reference_path.write_text(json.dumps(reference), encoding="utf-8")
        results = [
            {"board": reference, "capture_start_ns": 0},
            {"board": covered, "capture_start_ns": 0},
            {"board": reference, "capture_start_ns": 0},
            {"board": reference, "capture_start_ns": time.perf_counter_ns() + 10**9},
        ]
        with patch.object(sys, "argv", ["recovery_probe", "--reference", str(reference_path),
                                       "--output", str(output_path), "--trials", "1"]), \
             patch("builtins.input", return_value=""), \
             patch.object(recovery_probe, "board_from_api", side_effect=results) as api, \
             patch.object(recovery_probe.time, "sleep"), \
             contextlib.redirect_stdout(io.StringIO()):
            recovery_probe.main()
        self.assertEqual(api.call_count, 4)
        row = read_csv(output_path)[0]
        self.assertEqual(row["result"], "match")
        self.assertGreaterEqual(float(row["manual_key_to_api_match_ms"]), 0)


if __name__ == "__main__":
    unittest.main()
