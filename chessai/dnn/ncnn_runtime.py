# chessai/dnn/ncnn_runtime.py
from __future__ import annotations
from typing import Optional, Sequence, Tuple
import numpy as np

class NCNNRuntime:
    def __init__(
        self,
        param_path: str,
        bin_path: str,
        num_threads: int = 4,
        use_gpu: bool = False,
    ) -> None:
        self.param_path = param_path
        self.bin_path = bin_path
        self.num_threads = num_threads
        self.use_gpu = use_gpu
        self._net = None

    def load(self) -> None:
        """Load the NCNN model and prepare the net."""
        raise NotImplementedError

    def infer(self, image: np.ndarray) -> list:
        """Run inference and return raw NCNN outputs."""
        raise NotImplementedError

    def close(self) -> None:
        """Release the net."""
        raise NotImplementedError
