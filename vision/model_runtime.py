from dataclasses import dataclass, field
from typing import Any, Protocol

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Box


@dataclass(frozen=True)
class ModelDetection:
    label: str
    confidence: float
    box: Box
    data: dict[str, Any] = field(default_factory=dict)


class ObjectDetectionRuntime(Protocol):
    """
    Runtime interface for object detection models.

    Implementations may use TFLite, OpenCV DNN, ONNX, or another backend.
    """

    def detect(self, frame: Frame) -> list[ModelDetection]: ...
