# chessai/game/pikafish_engine.py
from __future__ import annotations
import subprocess
import time
from typing import Optional

from chessai.game.engine_base import EngineBase
from chessai.game.game_state import Player

class PikafishEngine(EngineBase):
    def __init__(
        self,
        engine_path: str,
        time_limit_ms: int = 2000,
        startup_timeout: float = 5.0,
        max_restarts: int = 5,
    ) -> None:
        self.engine_path = engine_path
        self.time_limit_ms = time_limit_ms
        self.startup_timeout = startup_timeout
        self.max_restarts = max_restarts
        self._process: Optional[subprocess.Popen] = None
        self._restart_count = 0
        self._last_fen = "startpos"

    def start(self) -> None:
        """Launch the Pikafish process."""
        raise NotImplementedError

    def stop(self) -> None:
        """Terminate the process."""
        raise NotImplementedError

    def set_position(self, board_array, next_player: Player) -> str:
        """
        Convert board_array + next_player to FEN or the SDK-specific board format.
        Returns the engine position command payload.
        """
        raise NotImplementedError

    def get_best_move(
        self,
        board_array,
        next_player: Player,
        time_limit_ms: Optional[int] = None,
    ) -> Optional[str]:
        """Return best move, e.g. 'B3C5' or 'd2d4', depending on engine API."""
        raise NotImplementedError

    def is_healthy(self) -> bool:
        """Return True if engine process is alive and responsive."""
        raise NotImplementedError
