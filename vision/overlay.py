from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import cv2
import numpy as np
from numpy.typing import NDArray

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata

Color = tuple[int, int, int]

DEFAULT_COLOR: Final[Color] = (255, 0, 0)

DEFAULT_COLORS: Final[dict[str, Color]] = {
    "face": (0, 0, 255),
    "person": (0, 255, 0),
    "object": (0, 255, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
}


class OverlayError(Exception):
    """Raised when Vision metadata cannot be rendered onto a frame."""


@dataclass(frozen=True, slots=True)
class OverlayStyle:
    box_thickness: int = 2
    label_scale: float = 0.5
    label_thickness: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.box_thickness, bool) or not isinstance(
            self.box_thickness,
            int,
        ):
            raise TypeError("box_thickness must be an integer")

        if self.box_thickness <= 0:
            raise ValueError("box_thickness must be greater than zero")

        if isinstance(self.label_scale, bool) or not isinstance(
            self.label_scale,
            int | float,
        ):
            raise TypeError("label_scale must be a number")

        label_scale = float(self.label_scale)

        if not math.isfinite(label_scale):
            raise ValueError("label_scale must be finite")

        if label_scale <= 0:
            raise ValueError("label_scale must be greater than zero")

        if isinstance(self.label_thickness, bool) or not isinstance(
            self.label_thickness,
            int,
        ):
            raise TypeError("label_thickness must be an integer")

        if self.label_thickness <= 0:
            raise ValueError("label_thickness must be greater than zero")

        object.__setattr__(
            self,
            "label_scale",
            label_scale,
        )


class OverlayRenderer:
    """
    Draw Vision metadata onto frame images.

    Detectors produce metadata. OverlayRenderer visualizes that metadata.
    It does not run detection and does not own the camera.
    """

    def __init__(
        self,
        style: OverlayStyle | None = None,
    ) -> None:
        if style is not None and not isinstance(
            style,
            OverlayStyle,
        ):
            raise TypeError("style must be an OverlayStyle")

        self.style = style if style is not None else OverlayStyle()

    def draw_metadata(
        self,
        frame: Frame,
        metadata: Metadata,
    ) -> Frame:
        if not isinstance(frame, Frame):
            raise TypeError("frame must be a Frame instance")

        if not isinstance(metadata, Metadata):
            raise TypeError("metadata must be a Metadata instance")

        image = frame.image

        if not isinstance(image, np.ndarray):
            raise TypeError("frame image must be a NumPy array")

        if image.ndim != 3 or image.shape[2] != 3:
            raise OverlayError("overlay rendering requires a three-channel image")

        try:
            rendered_image = image.copy()

            for detection in metadata.detections:
                self._draw_detection(
                    rendered_image,
                    detection,
                )

        except (
            cv2.error,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise OverlayError(f"failed to render Vision overlay: {exc}") from exc

        return Frame(
            image=rendered_image,
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
        x2 = min(
            image_width - 1,
            x + width,
        )
        y2 = min(
            image_height - 1,
            y + height,
        )

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
            label_y = min(
                image_height - 1,
                y1 + 16,
            )

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
