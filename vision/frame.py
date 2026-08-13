from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Self

import numpy as np

ImageArray = np.ndarray[
    tuple[int, ...],
    np.dtype[np.uint8],
]


@dataclass(
    frozen=True,
    slots=True,
)
class Frame:
    """
    Frame produced by the Vision pipeline.
    """

    image: ImageArray
    timestamp: float

    @classmethod
    def create(
        cls,
        image: ImageArray,
        *,
        timestamp: float | None = None,
    ) -> Self:
        return cls(
            image=image,
            timestamp=time() if timestamp is None else timestamp,
        )
