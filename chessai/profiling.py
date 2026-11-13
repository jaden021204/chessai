"""Opt-in timing records for the running application."""
import csv
import logging
import os
import platform
import re
import subprocess
import threading
import time
from contextlib import contextmanager, nullcontext
from functools import wraps
from pathlib import Path

import psutil


log = logging.getLogger(__name__)
profiler = None
_engine_local = threading.local()


def span(frame, name):
    return frame.measure(name) if frame is not None else nullcontext()


def measure_engine(operation):
    def decorate(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            active = profiler
            if active is None:
                return function(*args, **kwargs)
            _engine_local.command_start = None
            _engine_local.command_ms = None
            start = time.perf_counter_ns()
            outcome = "error"
            try:
                result = function(*args, **kwargs)
                outcome = "ok"
                return result
            finally:
                end = time.perf_counter_ns()
                active.record_engine(operation, kwargs.get("depth") if operation == "search" else "",
                                     (end - start) / 1e6, _engine_local.command_ms,
                                     outcome, start, end)
        return wrapper
    return decorate


def engine_command_start():
    if profiler is not None:
        _engine_local.command_start = time.perf_counter_ns()


def engine_command_end():
    if profiler is not None and getattr(_engine_local, "command_start", None) is not None:
        _engine_local.command_ms = (time.perf_counter_ns() - _engine_local.command_start) / 1e6


class Frame:
    def __init__(self, owner, capture):
        self.owner = owner
        self.capture = capture
        self.start_ns = time.perf_counter_ns()
        self.times = {}

    @contextmanager
    def measure(self, name):
        start = time.perf_counter_ns()
        try:
            yield
        finally:
            self.times[name] = (time.perf_counter_ns() - start) / 1e6

    def finish(self):
        end = time.perf_counter_ns()
        row = dict(self.capture)
        row.update(self.times)
        row["canvas_publish_ns"] = end
        row["processing_ms"] = (end - self.start_ns) / 1e6
        row["capture_start_to_canvas_ms"] = (end - row["capture_start_ns"]) / 1e6
        self.owner.record_frame(row)


class Profiler:
    FRAME_FIELDS = [
        "capture_id", "capture_start_ns", "capture_end_ns", "capture_read_ms",
        "capture_width", "capture_height", "homography_attempted", "warp_applied",
        "capture_to_processing_ms", "align_ms", "preprocess_ms",
        "ncnn_input_ms", "ncnn_extract_ms", "ncnn_output_copy_ms",
        "postprocess_ms", "detection_overlay_ms", "grid_snap_ms",
        "grid_overlay_ms", "debug_render_ms", "board_render_ms",
        "processing_ms", "capture_start_to_canvas_ms", "canvas_publish_ns",
    ]
    RESOURCE_FIELDS = [
        "timestamp_ns", "system_cpu_percent", "system_used_gib",
        "system_available_gib", "swap_used_gib", "process_tree_rss_gib",
        "temperature_c", "arm_clock_hz", "throttled_hex", "errors",
    ]
    ENGINE_FIELDS = ["operation", "depth", "total_ms", "uci_command_ms", "outcome",
                     "start_ns", "end_ns"]

    def __init__(self, directory, frames=1000, warmup=20):
        if frames < 1 or warmup < 0:
            raise ValueError("Profile frame count must be positive and warmup nonnegative.")
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=False)
        self.frames = frames
        self.warmup = warmup
        self.lock = threading.Lock()
        self.last_capture_id = None
        self.seen = 0
        self.saved = 0
        self.closed = False
        self.write_failed = False
        self.files = {}
        self.writers = {}
        for name, fields in (("frames", self.FRAME_FIELDS),
                             ("resources", self.RESOURCE_FIELDS),
                             ("engine", self.ENGINE_FIELDS)):
            file = (self.directory / f"{name}.csv").open("x", newline="", encoding="utf-8")
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            file.flush()
            self.files[name] = file
            self.writers[name] = writer
        (self.directory / "metadata.txt").write_text(
            f"platform={platform.platform()}\npython={platform.python_version()}\n"
            f"requested_frames={frames}\nwarmup_distinct_frames={warmup}\n"
            f"pid={os.getpid()}\nclock=perf_counter_ns\n"
            "ncnn_vulkan=false (application detector configuration)\n",
            encoding="utf-8",
        )
        self.stop_event = threading.Event()
        self.resource_thread = threading.Thread(target=self.sample_resources, daemon=True)
        self.resource_thread.start()
        log.warning("Profiling enabled; results will be saved in %s", self.directory)

    def write(self, name, row):
        with self.lock:
            if self.closed or self.write_failed:
                return False
            try:
                self.writers[name].writerow(row)
                self.files[name].flush()
                return True
            except (OSError, ValueError):
                log.exception("Profiling output failed for %s", name)
                self.write_failed = True
                return False

    def new_frame(self, capture):
        if capture is None:
            return None
        with self.lock:
            if self.closed or self.write_failed or self.saved >= self.frames or capture["capture_id"] == self.last_capture_id:
                return None
            self.last_capture_id = capture["capture_id"]
            self.seen += 1
            if self.seen <= self.warmup:
                return None
        frame = Frame(self, capture)
        frame.capture["capture_to_processing_ms"] = (frame.start_ns - capture["capture_end_ns"]) / 1e6
        return frame

    def record_frame(self, row):
        if not self.write("frames", row):
            return
        with self.lock:
            self.saved += 1
            if self.saved == self.frames:
                log.warning("Profiling collected %d distinct frames; engine/resource logging continues until shutdown.", self.saved)

    def record_engine(self, operation, depth, total_ms, uci_ms, outcome, start_ns, end_ns):
        self.write("engine", {"operation": operation, "depth": depth,
                              "total_ms": total_ms, "uci_command_ms": uci_ms,
                              "outcome": outcome, "start_ns": start_ns, "end_ns": end_ns})

    @staticmethod
    def firmware(command):
        try:
            result = subprocess.run(["vcgencmd", *command], capture_output=True,
                                    text=True, timeout=1, check=True)
            return result.stdout.strip(), None
        except (OSError, subprocess.SubprocessError) as exc:
            return "", f"vcgencmd {' '.join(command)}: {exc}"

    def sample_resources(self):
        try:
            self._sample_resources()
        except (psutil.Error, OSError, ValueError):
            log.exception("Profiling resource sampler stopped unexpectedly.")
            self.write("resources", {"timestamp_ns": time.perf_counter_ns(),
                                     "errors": "Resource sampler stopped unexpectedly; inspect application logs."})

    def _sample_resources(self):
        psutil.cpu_percent(interval=None)
        process = psutil.Process()
        while not self.stop_event.wait(1):
            errors = []
            memory = psutil.virtual_memory()
            rss = 0
            for child in [process] + process.children(recursive=True):
                try:
                    rss += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                    errors.append(f"process memory unavailable: {exc}")
            temperature, error = self.firmware(["measure_temp"])
            if error:
                errors.append(error)
            clock, error = self.firmware(["measure_clock", "arm"])
            if error:
                errors.append(error)
            throttled, error = self.firmware(["get_throttled"])
            if error:
                errors.append(error)
            temperature_value = temperature.removeprefix("temp=").removesuffix("'C")
            clock_value = clock.partition("=")[2]
            throttle_value = throttled.partition("=")[2]
            if temperature and not re.fullmatch(r"-?\d+(?:\.\d+)?", temperature_value):
                errors.append(f"Unexpected temperature response: {temperature}")
                temperature_value = ""
            if clock and not clock_value.isdigit():
                errors.append(f"Unexpected clock response: {clock}")
                clock_value = ""
            if throttled and not re.fullmatch(r"0x[0-9a-fA-F]+", throttle_value):
                errors.append(f"Unexpected throttling response: {throttled}")
                throttle_value = ""
            self.write("resources", {
                "timestamp_ns": time.perf_counter_ns(),
                "system_cpu_percent": psutil.cpu_percent(interval=None),
                "system_used_gib": (memory.total - memory.available) / 2**30,
                "system_available_gib": memory.available / 2**30,
                "swap_used_gib": psutil.swap_memory().used / 2**30,
                "process_tree_rss_gib": rss / 2**30,
                "temperature_c": temperature_value,
                "arm_clock_hz": clock_value,
                "throttled_hex": throttle_value,
                "errors": "; ".join(errors),
            })

    def close(self):
        self.stop_event.set()
        self.resource_thread.join(timeout=5)
        if self.resource_thread.is_alive():
            log.error("Profiling resource sampler did not stop.")
            return
        with self.lock:
            self.closed = True
            for file in self.files.values():
                file.close()
