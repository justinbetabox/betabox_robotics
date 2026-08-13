from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Protocol, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from betabox_robotics.vision.frame import (
    Frame,
    ImageArray,
)
from betabox_robotics.vision.model_runtime import ModelDetection


class _TFLiteInterpreter(Protocol):
    def allocate_tensors(self) -> None: ...

    def get_input_details(self) -> list[dict[str, object]]: ...

    def get_output_details(self) -> list[dict[str, object]]: ...

    def set_tensor(
        self,
        tensor_index: int,
        value: NDArray[np.generic],
    ) -> None: ...

    def invoke(self) -> None: ...

    def get_tensor(
        self,
        tensor_index: int,
    ) -> NDArray[np.generic]: ...


class TFLiteRuntimeError(RuntimeError):
    """Raised when TensorFlow Lite model operations fail."""


def _validate_existing_file(
    value: str | Path,
    *,
    name: str,
) -> Path:
    path = Path(value).expanduser()

    if not path.is_file():
        raise ValueError(f"{name} does not exist: {path}")

    return path


def _validate_input_size(
    value: object,
) -> tuple[int, int]:
    if not isinstance(value, tuple):
        raise TypeError("input_size must be a tuple of two integers")

    values = cast(
        tuple[object, ...],
        value,
    )

    if len(values) != 2:
        raise TypeError("input_size must be a tuple of two integers")

    width_value = values[0]
    height_value = values[1]

    if (
        isinstance(width_value, bool)
        or not isinstance(width_value, int)
        or isinstance(height_value, bool)
        or not isinstance(height_value, int)
    ):
        raise TypeError("input_size must contain two integers")

    if width_value <= 0 or height_value <= 0:
        raise ValueError("input_size values must be greater than 0")

    return (
        width_value,
        height_value,
    )


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


def _get_attribute(
    obj: object,
    name: str,
) -> object:
    return cast(
        object,
        getattr(
            obj,
            name,
        ),
    )


class TFLiteObjectDetectionModel:
    """
    TensorFlow Lite object detection runtime.

    Converts Betabox Vision frames into model input, runs inference,
    and converts model output into ModelDetection objects.

    This runtime performs inference only. It does not own the camera,
    acquire frames, or publish metadata.
    """

    model_path: Path
    labels_path: Path
    input_size: tuple[int, int]
    confidence_threshold: float

    labels: dict[int, str]

    interpreter: _TFLiteInterpreter
    input_details: list[dict[str, object]]
    output_details: list[dict[str, object]]

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
                "TensorFlow Lite object detection model must expose at least three output tensors"
            )

    @staticmethod
    def _numeric_value(
        value: object,
        *,
        name: str,
    ) -> int | float:
        if isinstance(value, bool):
            raise TFLiteRuntimeError(
                f"TensorFlow Lite model returned an invalid {name}"
            )

        if isinstance(value, int | float):
            return value

        if isinstance(
            value,
            np.integer | np.floating,
        ):
            scalar = cast(
                object,
                value.item(),
            )

            if isinstance(scalar, bool) or not isinstance(
                scalar,
                int | float,
            ):
                raise TFLiteRuntimeError(
                    f"TensorFlow Lite model returned an invalid {name}"
                )

            return scalar

        raise TFLiteRuntimeError(f"TensorFlow Lite model returned an invalid {name}")

    @staticmethod
    def _tensor_index(
        details: dict[str, object],
    ) -> int:
        value = details.get("index")

        if isinstance(value, bool) or not isinstance(
            value,
            int,
        ):
            raise TFLiteRuntimeError(
                "TensorFlow Lite model returned an invalid tensor index"
            )

        return value

    def detect(
        self,
        frame: Frame,
    ) -> list[ModelDetection]:
        input_tensor = self._preprocess(frame.image)

        try:
            index_value = self.input_details[0].get("index")

            if isinstance(index_value, bool) or not isinstance(
                index_value,
                int,
            ):
                raise TFLiteRuntimeError(
                    "TensorFlow Lite model returned an invalid input tensor index"
                )

            input_index = index_value

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
        image: ImageArray,
    ) -> NDArray[np.generic]:
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
            dtype_value = self.input_details[0].get("dtype")

            if not isinstance(dtype_value, type) or not issubclass(
                dtype_value,
                np.generic,
            ):
                raise TFLiteRuntimeError(
                    "TensorFlow Lite model returned an invalid input tensor dtype"
                )
        except (
            IndexError,
            KeyError,
            TypeError,
        ) as exc:
            raise TFLiteRuntimeError(
                "TensorFlow Lite model returned invalid input metadata"
            ) from exc

        if dtype_value is np.float32:
            return input_tensor.astype(np.float32) / 255.0

        return input_tensor.astype(dtype_value)

    def _decode_outputs(
        self,
        frame: Frame,
    ) -> list[ModelDetection]:
        try:
            boxes_tensor: NDArray[np.generic] = self.interpreter.get_tensor(
                self._tensor_index(
                    self.output_details[0],
                )
            )

            class_ids_tensor: NDArray[np.generic] = self.interpreter.get_tensor(
                self._tensor_index(
                    self.output_details[1],
                )
            )

            scores_tensor: NDArray[np.generic] = self.interpreter.get_tensor(
                self._tensor_index(
                    self.output_details[2],
                )
            )

            boxes = cast(
                NDArray[np.generic],
                cast(
                    object,
                    boxes_tensor[0],
                ),
            )

            class_ids = cast(
                NDArray[np.generic],
                cast(
                    object,
                    class_ids_tensor[0],
                ),
            )

            scores = cast(
                NDArray[np.generic],
                cast(
                    object,
                    scores_tensor[0],
                ),
            )

        except (
            IndexError,
            KeyError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise TFLiteRuntimeError(f"failed to read model outputs: {exc}") from exc

        detection_count = len(boxes)

        if detection_count != len(class_ids) or detection_count != len(scores):
            raise TFLiteRuntimeError(
                "TensorFlow Lite model returned mismatched detection outputs"
            )

        image = frame.image

        height: int = image.shape[0]
        width: int = image.shape[1]

        detections: list[ModelDetection] = []

        for index in range(detection_count):
            box = cast(
                NDArray[np.generic],
                cast(
                    object,
                    boxes[index],
                ),
            )

            score_value = self._numeric_value(
                cast(
                    object,
                    scores[index],
                ),
                name="detection score",
            )

            confidence = float(score_value)

            if not math.isfinite(confidence):
                continue

            if confidence < self.confidence_threshold:
                continue

            class_id_value = self._numeric_value(
                cast(
                    object,
                    class_ids[index],
                ),
                name="class ID",
            )

            class_index = int(class_id_value)

            if len(box) != 4:
                raise TFLiteRuntimeError(
                    "TensorFlow Lite model returned an invalid detection box"
                )

            box_values: list[float] = []

            for box_index in range(len(box)):
                box_values.append(
                    float(
                        self._numeric_value(
                            cast(
                                object,
                                box[box_index],
                            ),
                            name="detection box value",
                        )
                    )
                )

            y_min = box_values[0]
            x_min = box_values[1]
            y_max = box_values[2]
            x_max = box_values[3]

            x_min = min(
                1.0,
                max(
                    0.0,
                    x_min,
                ),
            )

            y_min = min(
                1.0,
                max(
                    0.0,
                    y_min,
                ),
            )

            x_max = min(
                1.0,
                max(
                    0.0,
                    x_max,
                ),
            )

            y_max = min(
                1.0,
                max(
                    0.0,
                    y_max,
                ),
            )

            if x_max <= x_min or y_max <= y_min:
                continue

            x = int(x_min * width)
            y = int(y_min * height)

            box_width = int((x_max - x_min) * width)
            box_height = int((y_max - y_min) * height)

            detections.append(
                ModelDetection(
                    label=self._label_for_class(
                        class_index,
                    ),
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
    ) -> _TFLiteInterpreter:
        try:
            module = importlib.import_module("tflite_runtime.interpreter")

        except ImportError:
            try:
                module = importlib.import_module("tensorflow.lite.python.interpreter")

            except ImportError as exc:
                raise TFLiteRuntimeError(
                    "no TensorFlow Lite interpreter found; install tflite-runtime or TensorFlow"
                ) from exc

        interpreter_class = _get_attribute(
            module,
            "Interpreter",
        )

        if not callable(interpreter_class):
            raise TFLiteRuntimeError("TensorFlow Lite Interpreter is not callable")

        try:
            interpreter = interpreter_class(
                model_path=str(path),
            )

        except (
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise TFLiteRuntimeError(
                f"failed to load TensorFlow Lite model {path}: {exc}"
            ) from exc

        return cast(
            _TFLiteInterpreter,
            interpreter,
        )
