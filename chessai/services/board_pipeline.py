# chessai/services/board_pipeline.py
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np

from chessai.vision.board_aligner import BoardAligner
from chessai.game.pikafish_engine import PikafishEngine
from chessai.game.game_state import GameState, Player
from chessai.vision.piece_detector import PieceDetector

class BoardPipelineService:
    def __init__(
        self,
        aligner: BoardAligner,
        detector: PieceDetector,
        engine: PikafishEngine,
        board_lock,
        frame_lock,
    ) -> None:
        self.aligner = aligner
        self.detector = detector
        self.engine = engine
        self.board_lock = board_lock
        self.frame_lock = frame_lock

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns:
            aligned_board_image, visualization_board, board_array
        """
        raise NotImplementedError

    def detect_board(self, frame: np.ndarray) -> np.ndarray:
        """Uses ARUCO alignment + NCNN detector to infer the 10x9 board state."""
        raise NotImplementedError

    def get_hint(self, game_state: GameState) -> Optional[str]:
        """Request engine hint for the current game."""
        raise NotImplementedError
