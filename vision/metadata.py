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
    detections: List[Detection] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source: str,
        *,
        detections: Optional[List[Detection]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> "Metadata":
        return cls(
            source=source,
            timestamp=time(),
            detections=detections or [],
            data=data or {},
        )
