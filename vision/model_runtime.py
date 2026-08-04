from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Box


@dataclass(frozen=True, slots=True)
class ModelDetection:
    label: str
    confidence: float
    box: Box
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.label, str):
            raise TypeError("label must be a string")

        normalized_label = self.label.strip()

        if not normalized_label:
            raise ValueError("label cannot be empty")

        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence,
            int | float,
        ):
            raise TypeError("confidence must be a number")

        confidence = float(self.confidence)

        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if not isinstance(self.box, tuple) or len(self.box) != 4:
            raise TypeError("box must be a tuple of four integers")

        if any(
            isinstance(value, bool) or not isinstance(value, int) for value in self.box
        ):
            raise TypeError("box must contain four integers")

        if not isinstance(self.data, dict):
            raise TypeError("data must be a dictionary")

        object.__setattr__(
            self,
            "label",
            normalized_label,
        )
        object.__setattr__(
            self,
            "confidence",
            confidence,
        )
        object.__setattr__(
            self,
            "data",
            dict(self.data),
        )


class ObjectDetectionModel(Protocol):
    """
    Backend interface for object detection models.

    Implementations perform inference only. They do not own the camera,
    manage frame acquisition, or publish metadata.

    Implementations may use TFLite, OpenCV DNN, ONNX, or another inference
    backend.
    """

    def detect(
        self,
        frame: Frame,
    ) -> Sequence[ModelDetection]: ...
