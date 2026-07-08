from abc import ABC, abstractmethod

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata


class Detector(ABC):
    """
    Interface for Vision detectors.

    Detectors analyze immutable frames and optionally return Metadata.
    They never own the camera, manage frame acquisition, or modify the
    original frame image.
    """

    def __init__(self, name: str, *, enabled: bool = False) -> None:
        self.name = name
        self.enabled = enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    @abstractmethod
    def detect(self, frame: Frame) -> Metadata | None:
        pass
