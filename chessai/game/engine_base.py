# chessai/game/engine_base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from chessai.game.game_state import GameState, Player

class EngineBase(ABC):
    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_position(self, board_array, next_player: Player) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_best_move(
        self,
        board_array,
        next_player: Player,
        time_limit_ms: Optional[int] = None,
    ) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def is_healthy(self) -> bool:
        raise NotImplementedError
