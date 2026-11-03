# chessai/dnn/yolo26s_ncnn.py
from __future__ import annotations
from typing import Optional, Sequence, Tuple
import cv2
import numpy as np

from chessai.dnn.ncnn_runtime import NCNNRuntime

class YOLO26sNCNNDetector:
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
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size
        self.num_threads = num_threads
        self.use_gpu = use_gpu

        self.param_path = f"{model_dir}/model.param"
        self.bin_path = f"{model_dir}/model.bin"
        self.runtime = NCNNRuntime(
            param_path=self.param_path,
            bin_path=self.bin_path,
            num_threads=num_threads,
            use_gpu=use_gpu,
        )

    def load(self) -> None:
        """Load the NCNN model."""
        self.runtime.load()

    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Resize while keeping aspect ratio, return padded image and scale."""
        raise NotImplementedError

    def postprocess(
        self,
        raw_outputs: list,
        original_shape: Tuple[int, int, int],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert raw NCNN predictions to boxes/scores/class_ids."""
        raise NotImplementedError

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
        raise NotImplementedError

    def close(self) -> None:
        self.runtime.close()
