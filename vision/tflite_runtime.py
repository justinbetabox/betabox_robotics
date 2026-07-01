from pathlib import Path

import cv2
import numpy as np

from betabox_car.vision.frame import Frame
from betabox_car.vision.model_runtime import ModelDetection


class TFLiteObjectDetectionRuntime:
    """
    TensorFlow Lite object detection runtime.

    Converts Betabox Vision frames into model input, runs inference,
    and converts model output into ModelDetection objects.
    """

    def __init__(
        self,
        model_path: str | Path,
        labels_path: str | Path,
        *,
        input_size: tuple[int, int] = (300, 300),
        confidence_threshold: float = 0.5,
    ) -> None:
        self.model_path = Path(model_path)
        self.labels_path = Path(labels_path)
        self.input_size = input_size
        self.confidence_threshold = float(confidence_threshold)

        self.labels = self._load_labels(self.labels_path)
        self.interpreter = self._load_interpreter(self.model_path)

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        self.interpreter.allocate_tensors()

    def detect(self, frame: Frame) -> list[ModelDetection]:
        image = frame.image

        input_tensor = self._preprocess(image)

        input_index = self.input_details[0]["index"]
        self.interpreter.set_tensor(input_index, input_tensor)
        self.interpreter.invoke()

        return self._decode_outputs(frame)

    def _preprocess(self, image) -> np.ndarray:
        resized = cv2.resize(image, self.input_size)
        input_tensor = np.expand_dims(resized, axis=0)

        dtype = self.input_details[0]["dtype"]

        if dtype == np.float32:
            input_tensor = input_tensor.astype(np.float32) / 255.0
        else:
            input_tensor = input_tensor.astype(dtype)

        return input_tensor

    def _decode_outputs(self, frame: Frame) -> list[ModelDetection]:
        boxes = self.interpreter.get_tensor(self.output_details[0]["index"])[0]
        class_ids = self.interpreter.get_tensor(self.output_details[1]["index"])[0]
        scores = self.interpreter.get_tensor(self.output_details[2]["index"])[0]

        height, width = frame.image.shape[:2]

        detections: list[ModelDetection] = []

        for box, class_id, score in zip(boxes, class_ids, scores):
            confidence = float(score)

            if confidence < self.confidence_threshold:
                continue

            y_min, x_min, y_max, x_max = box

            x = int(x_min * width)
            y = int(y_min * height)
            box_width = int((x_max - x_min) * width)
            box_height = int((y_max - y_min) * height)

            label = self._label_for_class(int(class_id))

            detections.append(
                ModelDetection(
                    label=label,
                    confidence=confidence,
                    box=(x, y, box_width, box_height),
                    data={
                        "class_id": int(class_id),
                    },
                )
            )

        return detections

    def _label_for_class(self, class_id: int) -> str:
        return self.labels.get(class_id, f"class_{class_id}")

    def _load_labels(self, path: Path) -> dict[int, str]:
        labels: dict[int, str] = {}

        with path.open("r", encoding="utf-8") as file:
            for index, line in enumerate(file, start=1):
                label = line.strip()

                if label:
                    labels[index] = label

        return labels

    def _load_interpreter(self, path: Path):
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            try:
                from tensorflow.lite.python.interpreter import Interpreter
            except ImportError as exc:
                raise RuntimeError(
                    "No TensorFlow Lite interpreter found. Install "
                    "tflite-runtime or TensorFlow."
                ) from exc

        return Interpreter(model_path=str(path))
