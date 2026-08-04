from abc import ABC, abstractmethod
from typing import Any

from betabox_robotics.vision.consumer import FrameConsumer


class StreamError(Exception):
    """Raised when a streaming operation fails."""


class Streamer(FrameConsumer, ABC):
    """
    Transport-independent streaming interface.

    Streamers consume frames from the Vision pipeline and deliver them to
    clients through WebRTC, MJPEG, RTSP, or another transport.
    """

    @abstractmethod
    def start(self) -> None:
        """Start accepting frames and serving stream clients."""

    @abstractmethod
    def stop(self) -> None:
        """Stop streaming and release transport resources."""

    @abstractmethod
    def clients(self) -> int:
        """Return the number of currently tracked stream clients."""

    @abstractmethod
    def statistics(self) -> dict[str, Any]:
        """Return current streamer diagnostics."""
