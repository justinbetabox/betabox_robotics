from abc import ABC, abstractmethod

from betabox_robotics.vision.frame import Frame


class FrameConsumer(ABC):
    """
    Interface for objects that consume frames from FrameSource.

    Streamers, recorders, and detection managers implement this interface
    so FrameSource can publish each completed frame without depending on
    concrete consumer implementations.
    """

    @abstractmethod
    def on_frame(self, frame: Frame) -> None:
        """Receive a frame from the Vision pipeline."""
