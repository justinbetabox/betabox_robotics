from typing import Protocol

from betabox_robotics.vision.frame import Frame


class FrameProvider(Protocol):
    """
    Structural interface for objects that expose the latest available frame.

    Implementations do not necessarily own the camera. They may provide a
    frame cached by any part of the Vision pipeline.
    """

    def latest_frame(self) -> Frame:
        """Return the latest available frame."""
        ...
