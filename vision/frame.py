from dataclasses import dataclass
from time import time
from typing import Any


@dataclass(frozen=True)
class Frame:
    """
    Captured camera frame.

    The image data format is implementation-dependent, but for the first
    Picamera2 implementation this will usually be a NumPy array.
    """

    image: Any
    timestamp: float

    @classmethod
    def create(cls, image: Any) -> "Frame":
        return cls(image=image, timestamp=time())
