from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

import cv2
import numpy as np
from numpy.typing import NDArray

from betabox_robotics.vision.detector import Detector
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata

HSVRange = tuple[
    tuple[int, int, int],
    tuple[int, int, int],
]


class ColorDetector(Detector):
    """
    Detect colored regions in frames and return structured metadata.

    This detector does not draw overlays. Other components may display,
    store, or ignore the resulting metadata.
    """

    DEFAULT_RANGES: ClassVar[dict[str, tuple[HSVRange, ...]]] = {
        "red": (
            ((0, 120, 70), (10, 255, 255)),
            ((170, 120, 70), (180, 255, 255)),
        ),
        "green": (((35, 80, 80), (85, 255, 255)),),
        "blue": (((90, 80, 80), (130, 255, 255)),),
        "yellow": (((20, 100, 100), (35, 255, 255)),),
    }

    def __init__(
        self,
        colors: str | Sequence[str] = "red",
        *,
        min_area: float = 500.0,
        enabled: bool = False,
    ) -> None:
        super().__init__("color", enabled=enabled)

        self.colors: list[str] = []
        self.min_area = 500.0

        self.configure(
            colors,
            min_area=min_area,
        )

    def detect(self, frame: Frame) -> Metadata:
        image = frame.image

        if len(image.shape) != 3 or image.shape[2] != 3:
            return Metadata.create(
                self.name,
                timestamp=frame.timestamp,
                data={
                    "colors": list(self.colors),
                    "count": 0,
                    "counts": {color: 0 for color in self.colors},
                    "error": "expected 3-channel image",
                },
            )

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2HSV,
        )

        all_detections: list[Detection] = []
        counts: dict[str, int] = {}

        for color in self.colors:
            detections = self._detect_color(
                hsv,
                color,
            )
            counts[color] = len(detections)
            all_detections.extend(detections)

        all_detections.sort(
            key=lambda detection: detection.data.get(
                "area",
                0,
            ),
            reverse=True,
        )

        return Metadata.create(
            self.name,
            timestamp=frame.timestamp,
            detections=all_detections,
            data={
                "colors": list(self.colors),
                "count": len(all_detections),
                "counts": counts,
            },
        )

    def _detect_color(
        self,
        hsv: NDArray[np.uint8],
        color: str,
    ) -> list[Detection]:
        mask: NDArray[np.uint8] | None = None

        for lower, upper in self.DEFAULT_RANGES[color]:
            current = cv2.inRange(
                hsv,
                lower,
                upper,
            )

            mask = current if mask is None else cv2.bitwise_or(mask, current)

        if mask is None:
            return []

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        detections: list[Detection] = []

        for contour in contours:
            area = float(cv2.contourArea(contour))

            if area < self.min_area:
                continue

            x, y, width, height = cv2.boundingRect(contour)

            detections.append(
                Detection(
                    label=color,
                    confidence=None,
                    box=(
                        int(x),
                        int(y),
                        int(width),
                        int(height),
                    ),
                    center=(
                        int(x + width // 2),
                        int(y + height // 2),
                    ),
                    data={
                        "area": area,
                        "color": color,
                    },
                )
            )

        return detections

    def configure(
        self,
        colors: str | Sequence[str] | None = None,
        *,
        min_area: float | None = None,
    ) -> None:
        if colors is not None:
            raw_colors = [colors] if isinstance(colors, str) else list(colors)

            color_list = [color.strip().casefold() for color in raw_colors]

            if not color_list:
                raise ValueError("at least one color is required")

            if any(not color for color in color_list):
                raise ValueError("color names cannot be empty")

            unsupported = [
                color for color in color_list if color not in self.DEFAULT_RANGES
            ]

            if unsupported:
                raise ValueError("unsupported color(s): " + ", ".join(unsupported))

            # Preserve order while removing duplicates.
            self.colors = list(dict.fromkeys(color_list))

        if min_area is not None:
            value = float(min_area)

            if value < 0:
                raise ValueError("min_area cannot be negative")

            self.min_area = value

    def enable(
        self,
        colors: str | Sequence[str] | None = None,
        *,
        min_area: float | None = None,
    ) -> None:
        self.configure(
            colors,
            min_area=min_area,
        )
        super().enable()
