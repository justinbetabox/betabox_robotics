from __future__ import annotations

import math

import cv2
import numpy as np

from betabox_robotics.vision.detector import (
    Detector,
    DetectorError,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import (
    Detection,
    Metadata,
)


def _validate_scale_factor(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("scale_factor must be a number")

    scale_factor = float(value)

    if not math.isfinite(scale_factor):
        raise ValueError("scale_factor must be finite")

    if scale_factor <= 1.0:
        raise ValueError("scale_factor must be greater than 1.0")

    return scale_factor


def _validate_min_neighbors(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("min_neighbors must be an integer")

    if value < 0:
        raise ValueError("min_neighbors cannot be negative")

    return value


def _validate_min_size(
    value: object,
) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TypeError("min_size must be a tuple of two integers")

    width, height = value

    if (
        isinstance(width, bool)
        or not isinstance(width, int)
        or isinstance(height, bool)
        or not isinstance(height, int)
    ):
        raise TypeError("min_size must contain two integers")

    if width <= 0 or height <= 0:
        raise ValueError("min_size dimensions must be positive")

    return width, height


class FaceDetector(Detector):
    """
    Detect faces in frames and return structured metadata.

    This detector does not draw overlays. It returns face locations for
    other Vision components to display, store, or ignore.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: tuple[int, int] = (30, 30),
    ) -> None:
        super().__init__(
            "face",
            enabled=enabled,
        )

        self.scale_factor = 1.1
        self.min_neighbors = 5
        self.min_size = (30, 30)

        self.configure(
            scale_factor=scale_factor,
            min_neighbors=min_neighbors,
            min_size=min_size,
        )

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

        try:
            cascade = cv2.CascadeClassifier(cascade_path)
        except cv2.error as exc:
            raise DetectorError(f"failed to load face cascade: {exc}") from exc

        if cascade.empty():
            raise DetectorError(f"failed to load face cascade: {cascade_path}")

        self._cascade = cascade

    def configure(
        self,
        *,
        scale_factor: float | None = None,
        min_neighbors: int | None = None,
        min_size: tuple[int, int] | None = None,
    ) -> None:
        if scale_factor is not None:
            self.scale_factor = _validate_scale_factor(scale_factor)

        if min_neighbors is not None:
            self.min_neighbors = _validate_min_neighbors(min_neighbors)

        if min_size is not None:
            self.min_size = _validate_min_size(min_size)

    def enable(
        self,
        *,
        scale_factor: float | None = None,
        min_neighbors: int | None = None,
        min_size: tuple[int, int] | None = None,
    ) -> None:
        self.configure(
            scale_factor=scale_factor,
            min_neighbors=min_neighbors,
            min_size=min_size,
        )
        super().enable()

    def detect(
        self,
        frame: Frame,
    ) -> Metadata:
        if not isinstance(frame, Frame):
            raise TypeError("frame must be a Frame instance")

        image = frame.image

        if not isinstance(image, np.ndarray):
            raise TypeError("frame image must be a NumPy array")

        if image.ndim != 3 or image.shape[2] != 3:
            return Metadata.create(
                self.name,
                timestamp=frame.timestamp,
                data={
                    "count": 0,
                    "error": ("expected 3-channel image"),
                },
            )

        try:
            gray = cv2.cvtColor(
                image,
                cv2.COLOR_RGB2GRAY,
            )

            faces = self._cascade.detectMultiScale(
                gray,
                scaleFactor=self.scale_factor,
                minNeighbors=self.min_neighbors,
                minSize=self.min_size,
            )

        except cv2.error as exc:
            raise DetectorError(f"face detection failed: {exc}") from exc

        detections: list[Detection] = []

        for x, y, width, height in faces:
            x_value = int(x)
            y_value = int(y)
            width_value = int(width)
            height_value = int(height)

            detections.append(
                Detection(
                    label="face",
                    confidence=None,
                    box=(
                        x_value,
                        y_value,
                        width_value,
                        height_value,
                    ),
                    center=(
                        x_value + width_value // 2,
                        y_value + height_value // 2,
                    ),
                    data={
                        "width": width_value,
                        "height": height_value,
                    },
                )
            )

        return Metadata.create(
            self.name,
            timestamp=frame.timestamp,
            detections=detections,
            data={
                "count": len(detections),
            },
        )
