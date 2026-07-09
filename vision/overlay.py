from __future__ import annotations

from dataclasses import dataclass

import cv2

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata

DEFAULT_COLORS = {
    "face": (0, 0, 255),      # blue
    "person": (0, 255, 0),    # green
    "object": (0, 255, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
}

@dataclass(frozen=True)
class OverlayStyle:
    box_thickness: int = 2
    label_scale: float = 0.5
    label_thickness: int = 1


class OverlayRenderer:
    """
    Draws Vision metadata onto frame images.

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

    def _draw_detection(self, image, detection: Detection) -> None:
        if detection.box is None:
            return

        x, y, width, height = detection.box

        # BGR green
        color = DEFAULT_COLORS.get(detection.label, (0, 255, 0))

        cv2.rectangle(
            image,
            (x, y),
            (x + width, y + height),
            color,
            self.style.box_thickness,
        )

        label = detection.label

        if detection.confidence is not None:
            label = f"{label} {detection.confidence:.2f}"

        cv2.putText(
            image,
            label,
            (x, max(0, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.style.label_scale,
            color,
            self.style.label_thickness,
            cv2.LINE_AA,
        )
