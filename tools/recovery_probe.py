#!/usr/bin/env python3
"""Estimate detected-board recovery after a manual key press, not screen latency."""
import argparse
import csv
import json
import time
from pathlib import Path
from urllib.request import urlopen


def board_from_api(url):
    with urlopen(url.rstrip("/") + "/api/vision/profile_board", timeout=5) as response:
        data = json.load(response)
    if not isinstance(data.get("board"), list) or not isinstance(data.get("capture_start_ns"), int):
        raise RuntimeError("A profiled detected board is not available.")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:5678")
    parser.add_argument("--reference", type=Path, required=True,
                        help="JSON file containing independently verified 10x9 board array")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    valid = {""} | {c + p for c in "rb" for p in "arnkbcp"}
    if (not isinstance(reference, list) or len(reference) != 10 or
            any(not isinstance(row, list) or len(row) != 9 or
                any(not isinstance(piece, str) or piece not in valid for piece in row)
                for row in reference)):
        parser.error("Reference must be a JSON 10x9 array of valid piece strings.")
    if args.trials < 1 or args.timeout <= 0:
        parser.error("Trials and timeout must be positive.")
    if board_from_api(args.url)["board"] != reference:
        raise RuntimeError("Current detected board does not match the independently verified reference.")
    with args.output.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["trial", "result", "manual_key_to_api_match_ms"])
        writer.writeheader()
        file.flush()
        for trial in range(1, args.trials + 1):
            input(f"Trial {trial}: cover pieces with your hand, wait for the displayed board to change, then press Enter. ")
            if board_from_api(args.url)["board"] == reference:
                print("Occlusion was not detected; this trial is recorded as not_occluded.")
                writer.writerow({"trial": trial, "result": "not_occluded", "manual_key_to_api_match_ms": ""})
                file.flush()
                continue
            input("Remove your hand, then immediately press Enter. ")
            start = time.perf_counter_ns()
            deadline = time.monotonic() + args.timeout
            result = None
            while time.monotonic() < deadline:
                current = board_from_api(args.url)
                if current["capture_start_ns"] >= start and current["board"] == reference:
                    result = (time.perf_counter_ns() - start) / 1e6
                    break
                time.sleep(0.02)
            writer.writerow({"trial": trial, "result": "match" if result is not None else "timeout",
                             "manual_key_to_api_match_ms": result if result is not None else ""})
            file.flush()
            print(f"API match: {result:.1f} ms after keypress" if result is not None else "No match before timeout.")
    print("Manual keypress and API polling do not measure hand-removal-to-screen latency.")


if __name__ == "__main__":
    main()
