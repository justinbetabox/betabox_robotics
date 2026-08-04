from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.model_runtime import ModelDetection


class TFLiteRuntimeError(RuntimeError):
    """Raised when TensorFlow Lite model operations fail."""


def _validate_existing_file(
    value: str | Path,
    *,
    name: str,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string or Path")

    path = Path(value).expanduser()

    if not path.is_file():
        raise ValueError(f"{name} does not exist: {path}")

    return path


def _validate_input_size(
    value: object,
) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TypeError("input_size must be a tuple of two integers")

    width, height = value

    if (
        isinstance(width, bool)
        or not isinstance(width, int)
        or isinstance(height, bool)
        or not isinstance(height, int)
    ):
        raise TypeError("input_size must contain two integers")

    if width <= 0 or height <= 0:
        raise ValueError("input_size values must be greater than 0")

    return width, height


def _validate_confidence_threshold(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("confidence_threshold must be a number")

    threshold = float(value)

    if not math.isfinite(threshold):
        raise ValueError("confidence_threshold must be finite")

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0.0 and 1.0")

    return threshold


class TFLiteObjectDetectionModel:
    """
    TensorFlow Lite object detection runtime.

    Converts Betabox Vision frames into model input, runs inference,
    and converts model output into ModelDetection objects.

    This runtime performs inference only. It does not own the camera,
    acquire frames, or publish metadata.
    """

    def __init__(
        self,
        model_path: str | Path,
        labels_path: str | Path,
        *,
        input_size: tuple[int, int] = (300, 300),
        confidence_threshold: float = 0.5,
    ) -> None:
        self.model_path = _validate_existing_file(
            model_path,
            name="model_path",
        )
        self.labels_path = _validate_existing_file(
            labels_path,
            name="labels_path",
        )
        self.input_size = _validate_input_size(input_size)
        self.confidence_threshold = _validate_confidence_threshold(confidence_threshold)

        self.labels = self._load_labels(self.labels_path)
        self.interpreter = self._load_interpreter(self.model_path)

        try:
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
        except (
            IndexError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise TFLiteRuntimeError(
                f"failed to initialize TensorFlow Lite model: {exc}"
            ) from exc

        if not self.input_details:
            raise TFLiteRuntimeError("TensorFlow Lite model has no input tensors")

        if len(self.output_details) < 3:
            raise TFLiteRuntimeError(
                "TensorFlow Lite object detection model "
                "must expose at least three output tensors"
            )

    def detect(
        self,
        frame: Frame,
    ) -> list[ModelDetection]:
        if not isinstance(frame, Frame):
            raise TypeError("frame must be a Frame instance")

        input_tensor = self._preprocess(frame.image)

        try:
            input_index = int(self.input_details[0]["index"])

            self.interpreter.set_tensor(
                input_index,
                input_tensor,
            )
            self.interpreter.invoke()

            return self._decode_outputs(frame)

        except TFLiteRuntimeError:
            raise

        except (
            IndexError,
            KeyError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise TFLiteRuntimeError(
                f"TensorFlow Lite inference failed: {exc}"
            ) from exc

    def _preprocess(
        self,
        image: Any,
    ) -> NDArray[Any]:
        if not isinstance(image, np.ndarray):
            raise TypeError("frame image must be a NumPy array")

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("frame image must have three color channels")

        try:
            resized = cv2.resize(
                image,
                self.input_size,
            )
        except cv2.error as exc:
            raise TFLiteRuntimeError(f"failed to resize model input: {exc}") from exc

        input_tensor = np.expand_dims(
            resized,
            axis=0,
        )

        try:
            dtype = self.input_details[0]["dtype"]
        except (
            IndexError,
            KeyError,
            TypeError,
        ) as exc:
            raise TFLiteRuntimeError(
                "TensorFlow Lite model returned invalid input metadata"
            ) from exc

        if dtype == np.float32:
            return input_tensor.astype(np.float32) / 255.0

        return input_tensor.astype(dtype)

    def _decode_outputs(
        self,
        frame: Frame,
    ) -> list[ModelDetection]:
        try:
            boxes = self.interpreter.get_tensor(self.output_details[0]["index"])[0]
            class_ids = self.interpreter.get_tensor(self.output_details[1]["index"])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]["index"])[0]
        except (
            IndexError,
            KeyError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise TFLiteRuntimeError(f"failed to read model outputs: {exc}") from exc

        if not (len(boxes) == len(class_ids) == len(scores)):
            raise TFLiteRuntimeError(
                "TensorFlow Lite model returned mismatched detection outputs"
            )

        image = frame.image

        if not isinstance(image, np.ndarray):
            raise TypeError("frame image must be a NumPy array")

        height, width = image.shape[:2]
        detections: list[ModelDetection] = []

        for box, class_id, score in zip(
            boxes,
            class_ids,
            scores,
        ):
            confidence = float(score)

            if not math.isfinite(confidence):
                continue

            if confidence < self.confidence_threshold:
                continue

            if len(box) != 4:
                raise TFLiteRuntimeError(
                    "TensorFlow Lite model returned an invalid detection box"
                )

            y_min, x_min, y_max, x_max = (float(value) for value in box)

            x_min = min(
                1.0,
                max(0.0, x_min),
            )
            y_min = min(
                1.0,
                max(0.0, y_min),
            )
            x_max = min(
                1.0,
                max(0.0, x_max),
            )
            y_max = min(
                1.0,
                max(0.0, y_max),
            )

            if x_max <= x_min or y_max <= y_min:
                continue

            x = int(x_min * width)
            y = int(y_min * height)
            box_width = int((x_max - x_min) * width)
            box_height = int((y_max - y_min) * height)

            class_index = int(class_id)

            detections.append(
                ModelDetection(
                    label=self._label_for_class(class_index),
                    confidence=confidence,
                    box=(
                        x,
                        y,
                        box_width,
                        box_height,
                    ),
                    data={
                        "class_id": class_index,
                    },
                )
            )

        return detections

    def _label_for_class(
        self,
        class_id: int,
    ) -> str:
        return self.labels.get(
            class_id,
            f"class_{class_id}",
        )

    @staticmethod
    def _load_labels(
        path: Path,
    ) -> dict[int, str]:
        labels: dict[int, str] = {}

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                for index, line in enumerate(file):
                    label = line.strip()

                    if label:
                        labels[index] = label

        except (
            OSError,
            UnicodeError,
        ) as exc:
            raise TFLiteRuntimeError(
                f"failed to load model labels from {path}: {exc}"
            ) from exc

        if not labels:
            raise TFLiteRuntimeError(f"model label file is empty: {path}")

        return labels

    @staticmethod
    def _load_interpreter(
        path: Path,
    ) -> Any:
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            try:
                from tensorflow.lite.python.interpreter import (
                    Interpreter,
                )
            except ImportError as exc:
                raise TFLiteRuntimeError(
                    "no TensorFlow Lite interpreter found; "
                    "install tflite-runtime or TensorFlow"
                ) from exc

        try:
            return Interpreter(model_path=str(path))
        except (
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise TFLiteRuntimeError(
                f"failed to load TensorFlow Lite model {path}: {exc}"
            ) from exc
