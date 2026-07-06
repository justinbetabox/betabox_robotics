from typing import Protocol

from betabox_robotics.vision.frame import Frame


class FrameProvider(Protocol):
    """Provides the latest available camera frame."""

    def latest_frame(self) -> Frame: ...
