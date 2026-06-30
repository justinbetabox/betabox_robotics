from typing import Protocol

from betabox_car.vision.frame import Frame


class FrameProvider(Protocol):
    """Provides the latest available camera frame."""

    def latest_frame(self) -> Frame: ...
