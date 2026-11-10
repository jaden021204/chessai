#!/usr/bin/env python3
import os
import sys
import time

for line in sys.stdin:
    command = line.strip()
    with open(os.environ["FAKE_ENGINE_LOG"], "a", encoding="utf-8") as log:
        log.write(command + "\n")
    if command == "uci":
        print("id name Fake Pikafish", flush=True)
        print("uciok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("position fen") and os.environ.get("FAKE_ENGINE_ERROR"):
        print("info string CRITICAL ERROR Invalid position", flush=True)
        sys.exit(1)
    elif command.startswith("go depth"):
        if os.environ.get("FAKE_ENGINE_TIMEOUT"):
            time.sleep(2)
        print("bestmove b2e2 ponder b9c7", flush=True)
    elif command == "quit":
        break
