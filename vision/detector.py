from abc import ABC, abstractmethod

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata


class Detector(ABC):
    """
    Interface for Vision detectors.

    Detectors analyze frames and return Metadata. They do not own the
    camera and should not draw directly onto frames.
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
