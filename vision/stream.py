from abc import ABC, abstractmethod
from typing import Any

from betabox_robotics.vision.consumer import FrameConsumer


class Streamer(FrameConsumer, ABC):
    """
    Transport-independent streaming interface.

    Streamers consume frames from the Vision pipeline and deliver them to
    clients using a transport such as WebRTC, MJPEG, RTSP, or a future
    streaming backend.
    """

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def clients(self) -> int:
        pass

    @abstractmethod
    def statistics(self) -> dict[str, Any]:
        pass
