from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Box


@dataclass(frozen=True, slots=True)
class ModelDetection:
    label: str
    confidence: float
    box: Box
    data: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_label = self.label.strip()

        if not normalized_label:
            raise ValueError("label cannot be empty")

        confidence = float(self.confidence)

        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

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
