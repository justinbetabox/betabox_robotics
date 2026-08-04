from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata


class DetectorError(Exception):
    """Raised when a detector cannot process a frame."""


class Detector(ABC):
    """
    Base interface for Vision detectors.

    Detectors analyze frames and optionally return Metadata. They do not own
    the camera, manage frame acquisition, or modify the original frame image.
    """

    def __init__(
        self,
        name: str,
        *,
        enabled: bool = False,
    ) -> None:
        if not isinstance(name, str):
            raise TypeError("detector name must be a string")

        normalized_name = name.strip()

        if not normalized_name:
            raise ValueError("detector name cannot be empty")

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean")

        self.name = normalized_name
        self._enabled = enabled
        self._state_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        with self._state_lock:
            return self._enabled

    def enable(self) -> None:
        with self._state_lock:
            self._enabled = True

    def disable(self) -> None:
        with self._state_lock:
            self._enabled = False

    @abstractmethod
    def detect(
        self,
        frame: Frame,
    ) -> Metadata | None:
        """Analyze a frame and return metadata when results are available."""
