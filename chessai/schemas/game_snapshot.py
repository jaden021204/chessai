# chessai/schemas/game_snapshot.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List

class GameSnapshot(BaseModel):
    is_playing: bool
    next_player: Optional[str] = None
    best_move: Optional[str] = None
    hint_move: Optional[str] = None
    board: Optional[List[List[str]]] = None
    status: Optional[str] = None
    evaluation: Optional[str] = None
