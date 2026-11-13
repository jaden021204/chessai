from __future__ import annotations

import cv2
import numpy as np

from chessai.config import (
    CELL_RECTANGLES,
    PIECE_DETECTION_CLASS_NAMES,
    PIECE_DETECTION_MODEL_PATH,
)
from chessai.dnn.yolo26s_ncnn import YOLO26sNCNNDetector
from chessai.profiling import span


class PieceDetector:
    def __init__(
        self,
        model_dir: str = PIECE_DETECTION_MODEL_PATH,
        class_names: list[str] = PIECE_DETECTION_CLASS_NAMES,
        score_thr: float = 0.35,
    ) -> None:
        self.class_names = list(class_names)
        if self.class_names != PIECE_DETECTION_CLASS_NAMES:
            raise ValueError(
                "Class names must match the 14 labels and order in config.py."
            )
        self.label_to_board_piece = {
            "B_A": "ba",
            "B_C": "bc",
            "B_E": "bb",
            "B_H": "bn",
            "B_K": "bk",
            "B_P": "bp",
            "B_R": "br",
            "R_A": "ra",
            "R_C": "rc",
            "R_E": "rb",
            "R_H": "rn",
            "R_K": "rk",
            "R_P": "rp",
            "R_R": "rr",
        }
        self.model = YOLO26sNCNNDetector(
            model_dir=model_dir,
            class_names=self.class_names,
            conf_threshold=score_thr,
        )
        self.model.load()

    @staticmethod
    def intersection_area(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        return max(0, x2 - x1) * max(0, y2 - y1)

    def detect(self, image, visualize=None, profile=None):
        boxes, scores, cls_inds = self.model.detect(image, visualize, profile=profile)

        with span(profile, "grid_snap_ms"):
            board = ["" for _ in CELL_RECTANGLES]
            for cell_index, rect in enumerate(CELL_RECTANGLES):
                cell_area = (rect[2] - rect[0]) * (rect[3] - rect[1])
                candidates = [
                    detection_index
                    for detection_index, box in enumerate(boxes)
                    if self.intersection_area(rect, box) > 0.3 * cell_area
                ]
                if candidates:
                    best_index = max(candidates, key=lambda i: scores[i])
                    class_id = int(cls_inds[best_index])
                    label = self.class_names[class_id]
                    board[cell_index] = self.label_to_board_piece[label]
            board = np.asarray(board, dtype=object).reshape(10, 9)

        with span(profile, "grid_overlay_ms"):
            if visualize is not None:
                for rect in CELL_RECTANGLES:
                    cv2.rectangle(
                        visualize,
                        (rect[0], rect[1]),
                        (rect[2], rect[3]),
                        (0, 255, 0),
                        2,
                    )

        return board
