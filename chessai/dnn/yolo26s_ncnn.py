# chessai/dnn/yolo26s_ncnn.py
from __future__ import annotations

from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

from chessai.dnn.ncnn_runtime import NCNNRuntime


class YOLO26sNCNNDetector:
    OUTPUT_NAME = "out0"
    CANDIDATE_COUNT = 8400
    OUTPUT_FEATURE_COUNT = 18

    def __init__(
        self,
        model_dir: str,
        class_names: Sequence[str],
        conf_threshold: float = 0.35,
        nms_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        num_threads: int = 4,
        use_gpu: bool = False,
    ) -> None:
        self.model_dir = model_dir
        self.class_names = list(class_names)
        if len(self.class_names) != 14:
            raise ValueError(
                f"YOLO26s model expects 14 class names, got {len(self.class_names)}."
            )
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size
        self.num_threads = num_threads
        self.use_gpu = use_gpu

        self.param_path = f"{model_dir}/model.ncnn.param"
        self.bin_path = f"{model_dir}/model.ncnn.bin"
        self.runtime = NCNNRuntime(
            param_path=self.param_path,
            bin_path=self.bin_path,
            num_threads=num_threads,
            use_gpu=use_gpu,
        )

    def load(self) -> None:
        """Load the NCNN model."""
        self.runtime.load()

    def preprocess(
        self, image: np.ndarray
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Return normalized RGB input, scale, and left/top letterbox padding."""
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Expected a color image with three channels.")

        image_height, image_width = image.shape[:2]
        if image_height == 0 or image_width == 0:
            raise ValueError("Cannot run detection on an empty image.")

        input_width, input_height = self.input_size
        scale = min(input_width / image_width, input_height / image_height)
        resized_width = int(round(image_width * scale))
        resized_height = int(round(image_height * scale))
        padding_x = (input_width - resized_width) // 2
        padding_y = (input_height - resized_height) // 2

        resized = cv2.resize(
            image,
            (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR,
        )
        resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        padded = np.full(
            (input_height, input_width, 3), 114, dtype=np.uint8
        )
        padded[
            padding_y : padding_y + resized_height,
            padding_x : padding_x + resized_width,
        ] = resized

        chw = padded.astype(np.float32).transpose(2, 0, 1) / 255.0
        return np.ascontiguousarray(chw), scale, (padding_x, padding_y)

    def postprocess(
        self,
        raw_outputs: Sequence[np.ndarray],
        original_shape: Tuple[int, int, int],
        scale: float,
        padding: Tuple[int, int],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Decode the exported (18, 8400) NCNN output and undo letterboxing."""
        if not raw_outputs:
            raise ValueError("The NCNN model returned no output tensors.")

        predictions = np.asarray(raw_outputs[0], dtype=np.float32)
        if predictions.ndim != 2:
            raise ValueError(
                f"Expected a 2D NCNN output, got shape {predictions.shape}."
            )
        if predictions.shape == (
            self.OUTPUT_FEATURE_COUNT,
            self.CANDIDATE_COUNT,
        ):
            predictions = predictions.T
        elif predictions.shape != (
            self.CANDIDATE_COUNT,
            self.OUTPUT_FEATURE_COUNT,
        ):
            raise ValueError(
                "Unexpected YOLO26s NCNN output shape "
                f"{predictions.shape}; expected (18, 8400) or (8400, 18)."
            )

        # This export returns decoded center-x, center-y, width, height followed
        # by 14 class probabilities. It has no separate objectness score.
        center_x, center_y, box_width, box_height = predictions[:, :4].T
        boxes = np.column_stack(
            (
                center_x - box_width / 2,
                center_y - box_height / 2,
                center_x + box_width / 2,
                center_y + box_height / 2,
            )
        )
        class_scores = predictions[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(len(class_scores)), class_ids]
        keep = scores >= self.conf_threshold
        boxes = boxes[keep]
        scores = scores[keep]
        class_ids = class_ids[keep]

        kept_indices = []
        for class_id in np.unique(class_ids):
            class_indices = np.flatnonzero(class_ids == class_id)
            kept_indices.extend(
                class_indices[self._nms(boxes[class_indices], scores[class_indices])]
            )

        if kept_indices:
            order = np.asarray(kept_indices, dtype=np.intp)
            order = order[np.argsort(scores[order])[::-1]]
            boxes = boxes[order]
            scores = scores[order]
            class_ids = class_ids[order]
        else:
            boxes = np.empty((0, 4), dtype=np.float32)
            scores = np.empty((0,), dtype=np.float32)
            class_ids = np.empty((0,), dtype=np.int64)

        padding_x, padding_y = padding
        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - padding_x) / scale
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - padding_y) / scale
        image_height, image_width = original_shape[:2]
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, image_width)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, image_height)

        return boxes, scores, class_ids

    def detect(
        self,
        image: np.ndarray,
        visualize: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns:
            boxes: np.ndarray, shape (N, 4)
            scores: np.ndarray, shape (N,)
            cls_inds: np.ndarray, shape (N,)
        """
        input_tensor, scale, padding = self.preprocess(image)
        raw_outputs = self.runtime.infer(input_tensor)
        boxes, scores, class_ids = self.postprocess(
            raw_outputs, image.shape, scale, padding
        )

        if visualize is not None:
            for box, score, class_id in zip(boxes, scores, class_ids):
                x1, y1, x2, y2 = np.rint(box).astype(int)
                cv2.rectangle(visualize, (x1, y1), (x2, y2), (0, 0, 255), 2)
                label = f"{self.class_names[int(class_id)]} {score:.2f}"
                cv2.putText(
                    visualize,
                    label,
                    (x1, max(y1 - 5, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

        return boxes, scores, class_ids

    def _nms(self, boxes: np.ndarray, scores: np.ndarray) -> np.ndarray:
        """Return indexes kept by class-specific non-maximum suppression."""
        order = np.argsort(scores)[::-1]
        kept = []

        while order.size:
            current = order[0]
            kept.append(current)
            remaining = order[1:]
            if remaining.size == 0:
                break

            left = np.maximum(boxes[current, 0], boxes[remaining, 0])
            top = np.maximum(boxes[current, 1], boxes[remaining, 1])
            right = np.minimum(boxes[current, 2], boxes[remaining, 2])
            bottom = np.minimum(boxes[current, 3], boxes[remaining, 3])
            intersection = np.maximum(0, right - left) * np.maximum(
                0, bottom - top
            )
            area_current = np.maximum(
                0, boxes[current, 2] - boxes[current, 0]
            ) * np.maximum(0, boxes[current, 3] - boxes[current, 1])
            area_remaining = np.maximum(
                0, boxes[remaining, 2] - boxes[remaining, 0]
            ) * np.maximum(0, boxes[remaining, 3] - boxes[remaining, 1])
            union = area_current + area_remaining - intersection
            overlap = np.divide(
                intersection,
                union,
                out=np.zeros_like(intersection),
                where=union > 0,
            )
            order = remaining[overlap <= self.nms_threshold]

        return np.asarray(kept, dtype=np.intp)

    def close(self) -> None:
        self.runtime.close()
