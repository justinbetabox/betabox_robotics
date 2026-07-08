from collections.abc import Sequence
from dataclasses import dataclass, field
from time import time
from typing import Any, Dict, List, Optional, Tuple

Box = Tuple[int, int, int, int]
Point = Tuple[int, int]


@dataclass(frozen=True)
class Detection:
    """
    Structured detection result.

    box format:
        (x, y, width, height)
    """

    label: str
    confidence: Optional[float] = None
    box: Optional[Box] = None
    center: Optional[Point] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Metadata:
    """
    Metadata produced from a frame.

    Detectors publish metadata instead of drawing overlays directly.
    """

    source: str
    timestamp: float
    detections: Sequence[Detection]
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source: str,
        *,
        detections: Sequence[Detection] | None = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> "Metadata":
        return cls(
            source=source,
            timestamp=time(),
            detections=tuple(detections) if detections is not None else (),
            data=data or {},
        )
