from __future__ import annotations

import cv2

from betabox_robotics.vision.detector import Detector
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata


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
        super().__init__("face", enabled=enabled)

        self.scale_factor = 1.1
        self.min_neighbors = 5
        self.min_size = (30, 30)

        self.configure(
            scale_factor=scale_factor,
            min_neighbors=min_neighbors,
            min_size=min_size,
        )

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

        self._cascade = cv2.CascadeClassifier(cascade_path)

        if self._cascade.empty():
            raise ValueError(f"failed to load face cascade: {cascade_path}")

    def configure(
        self,
        *,
        scale_factor: float | None = None,
        min_neighbors: int | None = None,
        min_size: tuple[int, int] | None = None,
    ) -> None:
        if scale_factor is not None:
            value = float(scale_factor)

            if value <= 1.0:
                raise ValueError("scale_factor must be greater than 1.0")

            self.scale_factor = value

        if min_neighbors is not None:
            value = int(min_neighbors)

            if value < 0:
                raise ValueError("min_neighbors cannot be negative")

            self.min_neighbors = value

        if min_size is not None:
            width, height = min_size

            if width <= 0 or height <= 0:
                raise ValueError("min_size dimensions must be positive")

            self.min_size = (
                int(width),
                int(height),
            )

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

    def detect(self, frame: Frame) -> Metadata:
        image = frame.image

        if len(image.shape) != 3 or image.shape[2] != 3:
            return Metadata.create(
                self.name,
                timestamp=frame.timestamp,
                data={
                    "count": 0,
                    "error": "expected 3-channel image",
                },
            )

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

        detections: list[Detection] = []

        for x, y, width, height in faces:
            x = int(x)
            y = int(y)
            width = int(width)
            height = int(height)

            detections.append(
                Detection(
                    label="face",
                    confidence=None,
                    box=(x, y, width, height),
                    center=(
                        x + width // 2,
                        y + height // 2,
                    ),
                    data={
                        "width": width,
                        "height": height,
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
