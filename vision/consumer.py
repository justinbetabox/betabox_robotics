from abc import ABC, abstractmethod

from betabox_robotics.vision.frame import Frame


class FrameConsumer(ABC):
    """
    Interface for objects that consume frames from FrameSource.

    Streamers, recorders, snapshot services, and detectors can all
    implement this interface.
    """

    @abstractmethod
    def on_frame(self, frame: Frame) -> None:
        pass
