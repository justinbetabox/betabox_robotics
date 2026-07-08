from dataclasses import dataclass
from time import time
from typing import Any


@dataclass(frozen=True)
class Frame:
    """
    Immutable frame produced by the Vision pipeline.

    A Frame represents a single moment in time captured from the camera.
    It is passed between Vision components without modification.

    The image format is implementation-defined. The current Betabox camera
    pipeline uses a NumPy ndarray in BGR color order.
    """

    image: Any
    timestamp: float

    @classmethod
    def create(cls, image: Any) -> "Frame":
        return cls(image=image, timestamp=time())
