from collections.abc import Sequence
from dataclasses import dataclass, field
from time import time
from typing import Self, TypeAlias

Box: TypeAlias = tuple[int, int, int, int]
Point: TypeAlias = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Detection:
    """
    Structured detection result.

    The optional box uses the format:

        (x, y, width, height)

    The data dictionary may contain detector-specific information that does
    not belong in the common detection fields.
    """

    label: str
    confidence: float | None = None
    box: Box | None = None
    center: Point | None = None
    data: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Metadata:
    """
    Metadata produced from a frame.

    Detectors publish structured metadata rather than drawing directly onto
    frame images. Streamers and other consumers may then decide how the
    metadata should be displayed or used.

    The data dictionary may contain source-specific information that does not
    belong in the common metadata fields.
    """

    source: str
    timestamp: float
    detections: tuple[Detection, ...] = ()
    data: dict[str, object] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source: str,
        *,
        timestamp: float | None = None,
        detections: Sequence[Detection] | None = None,
        data: dict[str, object] | None = None,
    ) -> Self:
        return cls(
            source=source,
            timestamp=time() if timestamp is None else timestamp,
            detections=tuple(detections) if detections is not None else (),
            data=dict(data) if data is not None else {},
        )
