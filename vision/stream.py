from abc import ABC, abstractmethod
from typing import Any, Dict

from betabox_car.vision.consumer import FrameConsumer


class Streamer(FrameConsumer, ABC):
    """
    Transport-independent streaming interface.

    Streamers consume frames from FrameSource.
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
    def statistics(self) -> Dict[str, Any]:
        pass
