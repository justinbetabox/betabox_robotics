from typing import Protocol

from betabox_robotics.vision.frame import Frame


class FrameProvider(Protocol):
    """
    Interface for objects that provide the latest available frame.

    Implementations do not necessarily own the camera. They simply expose
    the most recent frame from a Vision pipeline.
    """

    def latest_frame(self) -> Frame: ...
