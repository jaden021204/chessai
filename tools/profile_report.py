#!/usr/bin/env python3
"""Summarize measured frame, engine and Pi resource records."""
import argparse
import csv
import json
import statistics
from pathlib import Path


def load(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def stats(values):
    if not values:
        return None
    values = sorted(values)
    return {"count": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": values[max(0, (95 * len(values) + 99) // 100 - 1)],
            "max": values[-1]}


def numbers(rows, key):
    return [float(row[key]) for row in rows if row.get(key) not in ("", None)]


def sampled_status(values, threshold, rows):
    if any(value >= threshold for value in values):
        return "threshold reached or exceeded in samples"
    if len(rows) < 2 or len(values) != len(rows):
        return "inconclusive: missing or insufficient samples"
    return "below threshold in samples only; transients may be missed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    frames = load(args.directory / "frames.csv")
    engine = load(args.directory / "engine.csv")
    resources = load(args.directory / "resources.csv")
    metadata = (args.directory / "metadata.txt").read_text(encoding="utf-8")
    expected = int(dict(line.split("=", 1) for line in metadata.splitlines())["requested_frames"])
    if frames:
        start = int(frames[0]["capture_start_ns"])
        end = int(frames[-1]["canvas_publish_ns"])
        resources = [r for r in resources if start <= int(r["timestamp_ns"]) <= end]
    else:
        resources = []
    stages = [
        "capture_read_ms", "capture_to_processing_ms", "align_ms", "preprocess_ms",
        "ncnn_input_ms", "ncnn_extract_ms", "ncnn_output_copy_ms", "postprocess_ms",
        "detection_overlay_ms", "grid_snap_ms", "grid_overlay_ms", "debug_render_ms",
        "board_render_ms", "processing_ms", "capture_start_to_canvas_ms",
    ]
    processing_stages = [
        "align_ms", "preprocess_ms", "ncnn_input_ms", "ncnn_extract_ms",
        "ncnn_output_copy_ms", "postprocess_ms", "detection_overlay_ms",
        "grid_snap_ms", "grid_overlay_ms", "debug_render_ms", "board_render_ms",
    ]
    stage_means = {name: stats(numbers(frames, name)) for name in processing_stages}
    pie = {name: data["mean"] for name, data in stage_means.items() if data is not None}
    if len(pie) == len(processing_stages):
        pie["other_processing_ms"] = statistics.mean(
            float(row["processing_ms"]) - sum(float(row[name]) for name in processing_stages)
            for row in frames
        )
    throttle = [int(r["throttled_hex"], 16) for r in resources if r["throttled_hex"]]
    current_throttle = sum(bool(value & 0xE) for value in throttle)
    report = {
        "requested_frames": expected, "recorded_distinct_frames": len(frames),
        "complete": len(frames) == expected,
        "frames_ms": {name: stats(numbers(frames, name)) for name in stages},
        "processing_pie_mean_ms": pie,
        "homography_update_attempts": sum(r.get("homography_attempted") == "1" for r in frames),
        "warp_applied_frames": sum(r.get("warp_applied") == "1" for r in frames),
        "engine_ms": {
            operation: {
                "successful_count": len([r for r in engine if r["operation"] == operation and r["outcome"] == "ok"]),
                "failed_count": len([r for r in engine if r["operation"] == operation and r["outcome"] != "ok"]),
                "total_including_process_lifecycle": stats(numbers(
                    [r for r in engine if r["operation"] == operation and r["outcome"] == "ok"], "total_ms")),
                "uci_command_to_response": stats(numbers(
                    [r for r in engine if r["operation"] == operation and r["outcome"] == "ok"], "uci_command_ms")),
            } for operation in ("perft1", "search")
        },
        "resources": {name: stats(numbers(resources, name)) for name in (
            "system_cpu_percent", "system_used_gib", "system_available_gib",
            "swap_used_gib", "process_tree_rss_gib", "temperature_c", "arm_clock_hz")},
        "resource_samples": len(resources),
        "resource_window": "First recorded capture start through last recorded canvas publication.",
        "sampled_memory_14_decimal_gb": sampled_status(numbers(resources, "system_used_gib"), 14e9 / 2**30, resources),
        "sampled_temperature_80_c": sampled_status(numbers(resources, "temperature_c"), 80, resources),
        "current_frequency_cap_or_throttling_samples": current_throttle,
        "throttling_status": ("inconclusive: missing or insufficient samples"
                              if len(throttle) != len(resources) or len(resources) < 2
                              else "active throttling/capping observed" if current_throttle
                              else "no active capping/throttling in samples; transients may be missed"),
        "throttled_values": sorted({r["throttled_hex"] for r in resources if r["throttled_hex"]}),
        "resource_errors": sorted({r["errors"] for r in resources if r["errors"]}),
        "notes": [
            "GUI board_render_ms is server-side canvas drawing, not screen display latency.",
            "capture_read_ms includes driver wait/buffering and is not isolated USB decoding.",
            "ncnn_extract_ms is CPU-configured wall time around NCNN extraction, not CPU cycles.",
            "Engine events are not per-frame; do not add their mean to per-frame timing.",
            "Capture and processing are concurrent; stage means are not additive end-to-end latency.",
            "Missing resource values or throttling data cannot establish a pass.",
            "The 14 GB threshold is 14,000,000,000 bytes, not 14 GiB.",
            "Throttle bits 1-3 show current capping/throttling; bits 16-19 are historical since boot and may predate the run.",
            "CPU frequency normally varies with load; arm clock alone does not establish throttling.",
            "The processing pie excludes capture and engine; stage times are wall-clock and include scheduling.",
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
