import threading
from typing import Dict

from betabox_car.vision.consumer import FrameConsumer
from betabox_car.vision.detector import Detector
from betabox_car.vision.detectors import ColorDetector, FaceDetector
from betabox_car.vision.frame import Frame
from betabox_car.vision.metadata_bus import MetadataBus


class DetectionError(Exception):
    """Raised when detection operations fail."""


class DetectionManager(FrameConsumer):
    """
    Runs registered detectors against frames from the Vision pipeline.

    DetectionManager consumes frames from FrameSource and publishes
    detector results to MetadataBus.
    """

    def __init__(self, metadata_bus: MetadataBus) -> None:
        self.metadata_bus = metadata_bus
        self._detectors: Dict[str, Detector] = {}
        self._lock = threading.Lock()

        self.color = ColorDetector()
        self.face = FaceDetector()
        self.register(self.color)
        self.register(self.face)

    def register(self, detector: Detector) -> None:
        with self._lock:
            if detector.name in self._detectors:
                raise DetectionError(f"detector already registered: {detector.name}")

            self._detectors[detector.name] = detector

    def unregister(self, name: str) -> None:
        with self._lock:
            if name in self._detectors:
                del self._detectors[name]

    def enable(self, name: str) -> None:
        detector = self._get_detector(name)
        detector.enable()

    def disable(self, name: str) -> None:
        detector = self._get_detector(name)
        detector.disable()

    def is_enabled(self, name: str) -> bool:
        detector = self._get_detector(name)
        return detector.enabled

    def names(self) -> list[str]:
        with self._lock:
            return list(self._detectors.keys())

    def on_frame(self, frame: Frame) -> None:
        with self._lock:
            detectors = list(self._detectors.values())

        for detector in detectors:
            if not detector.enabled:
                continue

            metadata = detector.detect(frame)

            if metadata is not None:
                self.metadata_bus.publish(metadata)

    def _get_detector(self, name: str) -> Detector:
        with self._lock:
            detector = self._detectors.get(name)

        if detector is None:
            raise DetectionError(f"unknown detector: {name}")

        return detector
