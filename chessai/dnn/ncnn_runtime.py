# chessai/dnn/ncnn_runtime.py
from __future__ import annotations

from pathlib import Path

import ncnn
import numpy as np
from chessai.profiling import span


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
        self.close()
        net = ncnn.Net()
        net.opt.num_threads = self.num_threads
        net.opt.use_vulkan_compute = self.use_gpu

        param_path = Path(self.param_path)
        bin_path = Path(self.bin_path)
        if not param_path.is_file():
            raise FileNotFoundError(f"NCNN parameter file not found: {param_path}")
        if not bin_path.is_file():
            raise FileNotFoundError(f"NCNN weight file not found: {bin_path}")

        result = net.load_param(str(param_path))
        if result != 0:
            net.clear()
            raise RuntimeError(f"NCNN could not load parameter file: {param_path}")

        result = net.load_model(str(bin_path))
        if result != 0:
            net.clear()
            raise RuntimeError(f"NCNN could not load weight file: {bin_path}")

        self._net = net

    def infer(self, image: np.ndarray, profile=None) -> list:
        """Run inference and return raw NCNN outputs."""
        if self._net is None:
            raise RuntimeError("The NCNN model has not been loaded.")
        if image.dtype != np.float32 or image.ndim != 3:
            raise ValueError("NCNN input must be a 3D float32 CHW array.")

        with span(profile, "ncnn_input_ms"):
            input_mat = ncnn.Mat(np.ascontiguousarray(image))
            extractor = self._net.create_extractor()
            result = extractor.input("in0", input_mat)
        if result != 0:
            raise RuntimeError(f"NCNN could not set model input (code {result}).")

        with span(profile, "ncnn_extract_ms"):
            result, output = extractor.extract("out0")
        if result != 0:
            raise RuntimeError(f"NCNN could not extract model output (code {result}).")
        with span(profile, "ncnn_output_copy_ms"):
            result = [np.asarray(output).copy()]
        return result

    def close(self) -> None:
        """Release the net."""
        if self._net is not None:
            self._net.clear()
            self._net = None
