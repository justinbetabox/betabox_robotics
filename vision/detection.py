from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence

from typing_extensions import override

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.detector import (
    Detector,
    DetectorError,
)
from betabox_robotics.vision.detectors import (
    ColorDetector,
    FaceDetector,
    ObjectDetector,
)
from betabox_robotics.vision.detectors.color import (
    HSVRangeInput,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata_bus import MetadataBus


class DetectionError(DetectorError):
    """Raised when detector management or execution fails."""


def _validate_detector_name(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("detector name must be a string")

    name = value.strip()

    if not name:
        raise ValueError("detector name cannot be empty")

    return name


class DetectionManager(FrameConsumer):
    """
    Run registered detectors against frames from the Vision pipeline.

    DetectionManager consumes frames from FrameSource and publishes detector
    results to MetadataBus. It does not own the camera or modify frame images.
    """

    metadata_bus: MetadataBus

    _detectors: dict[str, Detector]
    _lock: threading.Lock

    color: ColorDetector
    face: FaceDetector
    objects: ObjectDetector

    def __init__(
        self,
        metadata_bus: MetadataBus,
    ) -> None:
        self.metadata_bus = metadata_bus
        self._detectors = {}
        self._lock = threading.Lock()

        self.color = ColorDetector()
        self.face = FaceDetector()
        self.objects = ObjectDetector()

        self.register(self.color)
        self.register(self.face)
        self.register(self.objects)

    def register(
        self,
        detector: Detector,
    ) -> None:
        with self._lock:
            if detector.name in self._detectors:
                raise DetectionError(f"detector already registered: {detector.name}")

            self._detectors[detector.name] = detector

    def unregister(
        self,
        name: str,
    ) -> None:
        detector_name = _validate_detector_name(name)

        with self._lock:
            _ = self._detectors.pop(
                detector_name,
                None,
            )

    def enable(
        self,
        name: str,
    ) -> None:
        self._get_detector(name).enable()

    def enable_color(
        self,
        colors: str | Sequence[str] | None = None,
        *,
        custom_ranges: Mapping[
            str,
            HSVRangeInput,
        ]
        | None = None,
        min_area: float | None = None,
    ) -> None:
        self.color.enable(
            colors,
            custom_ranges=custom_ranges,
            min_area=min_area,
        )

    def disable(
        self,
        name: str,
    ) -> None:
        self._get_detector(name).disable()

    def is_enabled(
        self,
        name: str,
    ) -> bool:
        return self._get_detector(name).enabled

    def names(
        self,
    ) -> list[str]:
        with self._lock:
            return list(self._detectors)

    @override
    def on_frame(
        self,
        frame: Frame,
    ) -> None:
        with self._lock:
            detectors = tuple(self._detectors.values())

        first_error: DetectionError | None = None
        first_cause: DetectorError | None = None

        for detector in detectors:
            if not detector.enabled:
                continue

            try:
                metadata = detector.detect(frame)

            except DetectorError as exc:
                if first_error is None:
                    first_error = DetectionError(
                        f"{detector.name} detector failed: {exc}"
                    )
                    first_cause = exc

                continue

            if metadata is not None:
                self.metadata_bus.publish(metadata)

        if first_error is not None:
            raise first_error from first_cause

    def _get_detector(
        self,
        name: str,
    ) -> Detector:
        detector_name = _validate_detector_name(name)

        with self._lock:
            detector = self._detectors.get(detector_name)

        if detector is None:
            raise DetectionError(f"unknown detector: {detector_name}")

        return detector
