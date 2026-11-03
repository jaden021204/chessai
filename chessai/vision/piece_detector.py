from __future__ import annotations
import cv2
import numpy as np

from chessai.common import *
from chessai.config import *
from chessai.dnn.yolo26s_ncnn import YOLO26sNCNNDetector

class PieceDetector:
    def __init__(
        self,
        model_dir: str,
        class_names: list[str],
        score_thr: float = 0.35,
        with_p6: bool = False,
    ) -> None:
        self.class_names = class_names
        self.model = YOLO26sNCNNDetector(
            model_dir=model_dir,
            class_names=class_names,
            conf_threshold=score_thr,
        )
        self.model.load()
        
    def detect(self, image, visualize=None):
        boxes, scores, cls_inds = self.model.detect(image, visualize)

        board = []
        for rect in CELL_RECTANGLES:
            is_found = False
            for i, box in enumerate(boxes):
                if self.intersection_area(rect, box) > 0.3 * (rect[2] - rect[0]) * (rect[3] - rect[1]):
                    cls_id = int(cls_inds[i])
                    piece_name = self.class_names[cls_id]
                    board.append(piece_name)
                    is_found = True
                    break

            if not is_found:
                board.append("")

        if visualize is not None:
            for rect in CELL_RECTANGLES:
                cv2.rectangle(visualize, (rect[0], rect[1]), (rect[2], rect[3]), (0, 255, 0), 2)

        board = np.array(board).reshape(10, 9)
        return board
