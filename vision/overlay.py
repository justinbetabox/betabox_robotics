from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata

DEFAULT_COLOR = (255, 0, 0)  # red

DEFAULT_COLORS = {
    "face": (0, 0, 255),  # blue
    "person": (0, 255, 0),  # green
    "object": (0, 255, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
}


@dataclass(frozen=True, slots=True)
class OverlayStyle:
    box_thickness: int = 2
    label_scale: float = 0.5
    label_thickness: int = 1

    def __post_init__(self) -> None:
        if self.box_thickness <= 0:
            raise ValueError("box_thickness must be greater than zero")

        if self.label_scale <= 0:
            raise ValueError("label_scale must be greater than zero")

        if self.label_thickness <= 0:
            raise ValueError("label_thickness must be greater than zero")


class OverlayRenderer:
    """
    Draw Vision metadata onto frame images.

    Detectors produce metadata. OverlayRenderer visualizes that metadata.
    It does not run detection and does not own the camera.
    """

    def __init__(self, style: OverlayStyle | None = None) -> None:
        self.style = style or OverlayStyle()

    def draw_metadata(self, frame: Frame, metadata: Metadata) -> Frame:
        image = frame.image.copy()

        for detection in metadata.detections:
            self._draw_detection(image, detection)

        return Frame(
            image=image,
            timestamp=frame.timestamp,
        )

    def _draw_detection(
        self,
        image: NDArray[np.uint8],
        detection: Detection,
    ) -> None:
        if detection.box is None:
            return

        x, y, width, height = detection.box
        image_height, image_width = image.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(image_width - 1, x + width)
        y2 = min(image_height - 1, y + height)

        if x2 <= x1 or y2 <= y1:
            return

        color = DEFAULT_COLORS.get(
            detection.label.casefold(),
            DEFAULT_COLOR,
        )

        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            color,
            self.style.box_thickness,
        )

        label = detection.label

        if detection.confidence is not None:
            label = f"{label} {detection.confidence:.2f}"

        label_y = y1 - 8

        if label_y < 12:
            label_y = min(image_height - 1, y1 + 16)

        cv2.putText(
            image,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.style.label_scale,
            color,
            self.style.label_thickness,
            cv2.LINE_AA,
        )
