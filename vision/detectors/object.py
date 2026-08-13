from __future__ import annotations

import math

from typing_extensions import override

from betabox_robotics.vision.detector import (
    Detector,
    DetectorError,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import (
    Detection,
    Metadata,
)
from betabox_robotics.vision.model_runtime import (
    ObjectDetectionModel,
)


def _validate_min_confidence(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("min_confidence must be a number")

    confidence = float(value)

    if not math.isfinite(confidence):
        raise ValueError("min_confidence must be finite")

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("min_confidence must be between 0.0 and 1.0")

    return confidence


class ObjectDetector(Detector):
    """
    Detect objects using a pluggable object detection model.

    The model owns backend-specific inference details. ObjectDetector
    adapts model results into Betabox Vision metadata.
    """

    model: ObjectDetectionModel | None
    min_confidence: float

    def __init__(
        self,
        model: ObjectDetectionModel | None = None,
        *,
        enabled: bool = False,
        min_confidence: float = 0.5,
    ) -> None:
        super().__init__(
            "objects",
            enabled=enabled,
        )

        self.model = model
        self.min_confidence = _validate_min_confidence(min_confidence)

    def configure(
        self,
        *,
        model: ObjectDetectionModel | None = None,
        min_confidence: float | None = None,
    ) -> None:
        if model is not None:
            self.model = model

        if min_confidence is not None:
            self.min_confidence = _validate_min_confidence(min_confidence)

    @override
    def enable(
        self,
        *,
        model: ObjectDetectionModel | None = None,
        min_confidence: float | None = None,
    ) -> None:
        self.configure(
            model=model,
            min_confidence=min_confidence,
        )
        super().enable()

    @override
    def detect(
        self,
        frame: Frame,
    ) -> Metadata:
        if self.model is None:
            return Metadata.create(
                self.name,
                timestamp=frame.timestamp,
                data={
                    "count": 0,
                    "error": ("object detection model is not configured"),
                },
            )

        try:
            model_detections = self.model.detect(frame)
        except (
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise DetectorError(f"object detection failed: {exc}") from exc

        detections: list[Detection] = []

        for result in model_detections:
            if result.confidence < self.min_confidence:
                continue

            x, y, width, height = result.box

            detections.append(
                Detection(
                    label=result.label,
                    confidence=result.confidence,
                    box=result.box,
                    center=(
                        x + width // 2,
                        y + height // 2,
                    ),
                    data=dict(result.data),
                )
            )

        return Metadata.create(
            self.name,
            timestamp=frame.timestamp,
            detections=detections,
            data={
                "count": len(detections),
                "min_confidence": (self.min_confidence),
            },
        )
