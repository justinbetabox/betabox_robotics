from __future__ import annotations

import threading

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.detector import Detector
from betabox_robotics.vision.detectors import (
    ColorDetector,
    FaceDetector,
    ObjectDetector,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata_bus import MetadataBus


class DetectionError(Exception):
    """Raised when detector management or execution fails."""


class DetectionManager(FrameConsumer):
    """
    Run registered detectors against frames from the Vision pipeline.

    DetectionManager consumes frames from FrameSource and publishes detector
    results to MetadataBus. It does not own the camera or modify frame images.
    """

    def __init__(self, metadata_bus: MetadataBus) -> None:
        self.metadata_bus = metadata_bus
        self._detectors: dict[str, Detector] = {}
        self._lock = threading.Lock()

        self.color = ColorDetector()
        self.face = FaceDetector()
        self.objects = ObjectDetector()

        self.register(self.color)
        self.register(self.face)
        self.register(self.objects)

    def register(self, detector: Detector) -> None:
        with self._lock:
            if detector.name in self._detectors:
                raise DetectionError(f"detector already registered: {detector.name}")

            self._detectors[detector.name] = detector

    def unregister(self, name: str) -> None:
        with self._lock:
            self._detectors.pop(name, None)

    def enable(self, name: str) -> None:
        self._get_detector(name).enable()

    def disable(self, name: str) -> None:
        self._get_detector(name).disable()

    def is_enabled(self, name: str) -> bool:
        return self._get_detector(name).enabled

    def names(self) -> list[str]:
        with self._lock:
            return list(self._detectors)

    def on_frame(self, frame: Frame) -> None:
        with self._lock:
            detectors = tuple(self._detectors.values())

        first_error: DetectionError | None = None

        for detector in detectors:
            if not detector.enabled:
                continue

            try:
                metadata = detector.detect(frame)
            except Exception as exc:
                if first_error is None:
                    first_error = DetectionError(
                        f"{detector.name} detector failed: {exc}"
                    )

                continue

            if metadata is not None:
                self.metadata_bus.publish(metadata)

        if first_error is not None:
            raise first_error

    def _get_detector(self, name: str) -> Detector:
        with self._lock:
            detector = self._detectors.get(name)

        if detector is None:
            raise DetectionError(f"unknown detector: {name}")

        return detector
