from __future__ import annotations

import queue
import re
import subprocess
import threading
import time
from typing import Optional

from chessai.game.engine_base import EngineBase
from chessai.game.game_state import Player
from chessai import profiling


class EngineError(RuntimeError):
    """The engine could not provide a usable result."""


class PikafishEngine(EngineBase):
    def __init__(
        self,
        engine_path: str,
        startup_timeout: float = 10.0,
        search_timeout: float = 60.0,
    ) -> None:
        self.engine_path = engine_path
        self.startup_timeout = startup_timeout
        self.search_timeout = search_timeout
        self._process: Optional[subprocess.Popen] = None
        self._lines = queue.Queue()
        self._lock = threading.Lock()

    def start(self) -> None:
        if self.is_healthy():
            return
        if not self.engine_path:
            raise EngineError("Set ENGINE_PATH to your Pikafish executable.")
        self._lines = queue.Queue()
        try:
            self._process = subprocess.Popen(
                [self.engine_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise EngineError(f"Could not start Pikafish: {exc}") from exc

        process = self._process
        lines = self._lines

        def read_output():
            for line in process.stdout:
                lines.put(line.rstrip())
            lines.put(None)

        threading.Thread(target=read_output, daemon=True).start()
        try:
            self._write("uci")
            self._wait_for("uciok", self.startup_timeout)
            self._write("isready")
            self._wait_for("readyok", self.startup_timeout)
        except (EngineError, OSError):
            self.stop()
            raise

    def _write(self, command: str) -> None:
        if self._process is None or self._process.stdin is None:
            raise EngineError("Pikafish is not running.")
        if self._process.poll() is not None:
            self._wait_for("__engine_exit__", 1)
            raise EngineError("Pikafish exited unexpectedly.")
        try:
            self._process.stdin.write(command + "\n")
            self._process.stdin.flush()
        except OSError as exc:
            try:
                self._wait_for("__engine_exit__", 1)
            except EngineError as output_error:
                raise output_error from exc
            raise EngineError(f"Could not communicate with Pikafish: {exc}") from exc

    def _wait_for(self, prefix: str, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        last_line = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EngineError(f"Pikafish timed out waiting for {prefix}.")
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise EngineError(f"Pikafish timed out waiting for {prefix}.") from exc
            if line is None:
                detail = f" Last output: {last_line}" if last_line else ""
                raise EngineError(f"Pikafish exited unexpectedly.{detail}")
            if "CRITICAL ERROR" in line.upper():
                raise EngineError(f"Pikafish rejected the position: {line}")
            if line == prefix or line.startswith(prefix + " "):
                return line
            if line:
                last_line = line

    def stop(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            try:
                process.stdin.write("quit\n")
                process.stdin.flush()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
                process.wait()
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()

    @staticmethod
    def board_array_to_fen(board_array, next_player: str) -> str:
        if next_player not in (Player.RED, Player.BLACK):
            raise ValueError("The side to move must be red or black.")
        if board_array is None or len(board_array) != 10 or any(
            len(row) != 9 for row in board_array
        ):
            raise ValueError("A detected 10 by 9 board is required.")
        valid = {color + piece for color in "rb" for piece in "arnkbcp"}
        counts = {}
        rows = []
        for row in board_array:
            empty = 0
            fen_row = ""
            for square in row:
                if not square:
                    empty += 1
                    continue
                if square not in valid:
                    raise ValueError(f"Unknown board piece: {square}")
                counts[square] = counts.get(square, 0) + 1
                if empty:
                    fen_row += str(empty)
                    empty = 0
                fen_row += square[1].upper() if square[0] == "r" else square[1]
            rows.append(fen_row + (str(empty) if empty else ""))
        for color in "rb":
            for piece, maximum in (("k", 1), ("a", 2), ("b", 2), ("n", 2),
                                   ("r", 2), ("c", 2), ("p", 5)):
                count = counts.get(color + piece, 0)
                if count > maximum or (piece == "k" and count != 1):
                    raise ValueError(f"Invalid number of {color + piece} pieces: {count}.")
        invalid = []
        kings = {}
        advisor_squares = {(0, 3), (0, 5), (1, 4), (2, 3), (2, 5)}
        elephant_squares = {(0, 2), (0, 6), (2, 0), (2, 4), (2, 8), (4, 2), (4, 6)}
        names = {"k": "king", "a": "advisor", "b": "elephant", "p": "pawn"}
        for row_index, row in enumerate(board_array):
            for col_index, square in enumerate(row):
                if not square:
                    continue
                color, piece = square
                # Normalize red's half to the same orientation as black's.
                r = row_index if color == "b" else 9 - row_index
                c = col_index if color == "b" else 8 - col_index
                if piece == "k":
                    kings[color] = (row_index, col_index)
                    wrong = r > 2 or not 3 <= c <= 5
                elif piece == "a":
                    wrong = (r, c) not in advisor_squares
                elif piece == "b":
                    wrong = (r, c) not in elephant_squares
                elif piece == "p":
                    wrong = r < 3 or (r <= 4 and c % 2 != 0)
                else:
                    wrong = False
                if wrong:
                    invalid.append(f"{'red' if color == 'r' else 'black'} {names[piece]}")
        if len(invalid) > 1:
            raise ValueError("MULTIPLE PIECES IN WRONG LOCATIONS: " + ", ".join(invalid) + ".")
        if invalid:
            raise ValueError(f"The {invalid[0]} is in an illegal position.")
        black_king, red_king = kings["b"], kings["r"]
        if black_king[1] == red_king[1] and not any(
            board_array[row][black_king[1]] for row in range(black_king[0] + 1, red_king[0])
        ):
            raise ValueError("The kings cannot face each other without a piece between them.")
        return "/".join(rows) + (" w" if next_player == Player.RED else " b")

    def set_position(self, board_array, next_player: str) -> str:
        fen = self.board_array_to_fen(board_array, next_player)
        self._write(f"position fen {fen}")
        return fen

    @profiling.measure_engine("search")
    def get_best_move(
        self,
        board_array,
        next_player: str,
        time_limit_ms: Optional[int] = None,
        *,
        depth: int = 4,
    ) -> Optional[str]:
        if time_limit_ms is not None:
            raise ValueError("Choose a search depth, not a time limit.")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
            raise ValueError("Search depth must be a positive integer.")
        fen = self.board_array_to_fen(board_array, next_player)
        with self._lock:
            try:
                self.start()
                self._write(f"position fen {fen}")
                self._write("isready")
                self._wait_for("readyok", self.startup_timeout)
                profiling.engine_command_start()
                self._write(f"go depth {depth}")
                result = self._wait_for("bestmove", self.search_timeout).split()
                profiling.engine_command_end()
                if len(result) < 2:
                    raise EngineError("Pikafish returned an incomplete bestmove.")
                move = result[1]
                if move in ("(none)", "0000"):
                    return None
                if not re.fullmatch(r"[a-i][0-9][a-i][0-9]", move) or move[:2] == move[2:]:
                    raise EngineError(f"Pikafish returned an invalid move: {move}")
                return move
            finally:
                self.stop()

    def get_move(self, game_state, *, depth: int = 4) -> Optional[str]:
        return self.get_best_move(game_state.board, game_state.next_player, depth=depth)

    @profiling.measure_engine("perft1")
    def legal_moves(self, board_array, next_player: str):
        fen = self.board_array_to_fen(board_array, next_player)
        with self._lock:
            try:
                self.start()
                self._write(f"position fen {fen}")
                self._write("isready")
                self._wait_for("readyok", self.startup_timeout)
                profiling.engine_command_start()
                self._write("go perft 1")
                deadline = time.monotonic() + self.search_timeout
                moves = set()
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise EngineError("Pikafish timed out listing legal moves.")
                    try:
                        line = self._lines.get(timeout=remaining)
                    except queue.Empty as exc:
                        raise EngineError("Pikafish timed out listing legal moves.") from exc
                    if line is None:
                        raise EngineError("Pikafish exited while listing legal moves.")
                    if "CRITICAL ERROR" in line.upper():
                        raise EngineError(f"Pikafish rejected the position: {line}")
                    match = re.fullmatch(r"([a-i][0-9][a-i][0-9]):\s*(\d+)", line)
                    if match:
                        moves.add(match.group(1))
                    elif line.startswith("Nodes searched:"):
                        profiling.engine_command_end()
                        try:
                            count = int(line.partition(":")[2].strip())
                        except ValueError as exc:
                            raise EngineError(f"Invalid Pikafish perft result: {line}") from exc
                        if count != len(moves):
                            raise EngineError("Pikafish returned an incomplete legal move list.")
                        return moves
            finally:
                self.stop()

    def is_healthy(self) -> bool:
        return self._process is not None and self._process.poll() is None
