from dataclasses import dataclass
from time import time
from typing import Any


@dataclass(frozen=True, slots=True)
class Frame:
    """
    Frame produced by the Vision pipeline.

    A Frame represents one camera image and the time at which it entered the
    Betabox Vision pipeline. Frame attributes cannot be reassigned, although
    the underlying image object may itself be mutable.

    The image format is implementation-defined. The current Betabox camera pipeline uses a NumPy ndarray in RGB
    channel order.
    """

    image: Any
    timestamp: float

    @classmethod
    def create(cls, image: Any, *, timestamp: float | None = None) -> "Frame":
        """
        Create a frame.

        A timestamp may be supplied when the capture time is already known.
        Otherwise, the current wall-clock time is used.
        """
        return cls(
            image=image,
            timestamp=time() if timestamp is None else timestamp,
        )
