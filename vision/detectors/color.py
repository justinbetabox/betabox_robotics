from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import ClassVar, TypeAlias

import cv2
import numpy as np
from numpy.typing import NDArray

from betabox_robotics.vision.detector import (
    Detector,
    DetectorError,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import (
    Detection,
    Metadata,
)

HSVValue: TypeAlias = tuple[int, int, int]
HSVRange: TypeAlias = tuple[HSVValue, HSVValue]
HSVRangeInput: TypeAlias = HSVRange | Sequence[HSVRange]


def _validate_hsv_value(
    value: object,
    *,
    name: str,
) -> HSVValue:
    if not isinstance(value, tuple) or len(value) != 3:
        raise TypeError(f"{name} must be a tuple of three integers")

    hue, saturation, brightness = value

    if any(
        isinstance(component, bool) or not isinstance(component, int)
        for component in value
    ):
        raise TypeError(f"{name} must contain three integers")

    if not 0 <= hue <= 180:
        raise ValueError(f"{name} hue must be between 0 and 180")

    if not 0 <= saturation <= 255:
        raise ValueError(f"{name} saturation must be between 0 and 255")

    if not 0 <= brightness <= 255:
        raise ValueError(f"{name} brightness must be between 0 and 255")

    return hue, saturation, brightness


def _validate_hsv_range(
    value: object,
    *,
    name: str,
) -> HSVRange:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TypeError(f"{name} must contain lower and upper HSV values")

    lower = _validate_hsv_value(
        value[0],
        name=f"{name} lower value",
    )
    upper = _validate_hsv_value(
        value[1],
        name=f"{name} upper value",
    )

    if any(
        lower_value > upper_value
        for lower_value, upper_value in zip(
            lower,
            upper,
        )
    ):
        raise ValueError(f"{name} lower values cannot exceed upper values")

    return lower, upper


def _is_single_hsv_range(
    value: object,
) -> bool:
    return (
        isinstance(value, tuple)
        and len(value) == 2
        and all(isinstance(bound, tuple) and len(bound) == 3 for bound in value)
    )


def _validate_custom_ranges(
    value: object,
) -> dict[str, tuple[HSVRange, ...]]:
    if not isinstance(value, Mapping):
        raise TypeError("custom_ranges must be a mapping")

    validated: dict[str, tuple[HSVRange, ...]] = {}

    for raw_name, raw_ranges in value.items():
        if not isinstance(raw_name, str):
            raise TypeError("custom color names must be strings")

        name = raw_name.strip().casefold()

        if not name:
            raise ValueError("custom color names cannot be empty")

        if _is_single_hsv_range(raw_ranges):
            ranges = (
                _validate_hsv_range(
                    raw_ranges,
                    name=f"{name} range",
                ),
            )
        else:
            if isinstance(
                raw_ranges,
                str | bytes,
            ) or not isinstance(
                raw_ranges,
                Sequence,
            ):
                raise TypeError(
                    f"{name} ranges must be an HSV range or sequence of HSV ranges"
                )

            if not raw_ranges:
                raise ValueError(f"{name} must define at least one HSV range")

            ranges = tuple(
                _validate_hsv_range(
                    hsv_range,
                    name=f"{name} range",
                )
                for hsv_range in raw_ranges
            )

        validated[name] = ranges

    return validated


def _validate_colors(
    value: str | Sequence[str],
    *,
    supported: Mapping[str, tuple[HSVRange, ...]],
) -> list[str]:
    if isinstance(value, str):
        raw_colors = [value]
    elif isinstance(value, Sequence):
        raw_colors = list(value)
    else:
        raise TypeError("colors must be a string or sequence of strings")

    if not raw_colors:
        raise ValueError("at least one color is required")

    if any(not isinstance(color, str) for color in raw_colors):
        raise TypeError("colors must contain only strings")

    colors = [color.strip().casefold() for color in raw_colors]

    if any(not color for color in colors):
        raise ValueError("color names cannot be empty")

    unsupported = [color for color in colors if color not in supported]

    if unsupported:
        raise ValueError("unsupported color(s): " + ", ".join(unsupported))

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(colors))


def _validate_min_area(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("min_area must be a number")

    min_area = float(value)

    if not math.isfinite(min_area):
        raise ValueError("min_area must be finite")

    if min_area < 0:
        raise ValueError("min_area cannot be negative")

    return min_area


class ColorDetector(Detector):
    """
    Detect colored regions in frames and return structured metadata.

    Built-in colors cover common classroom uses. Additional named colors may
    be supplied as one or more OpenCV HSV ranges.

    This detector does not draw overlays. Other components may display,
    store, or ignore the resulting metadata.
    """

    DEFAULT_RANGES: ClassVar[dict[str, tuple[HSVRange, ...]]] = {
        "red": (
            (
                (0, 120, 70),
                (10, 255, 255),
            ),
            (
                (170, 120, 70),
                (180, 255, 255),
            ),
        ),
        "orange": (
            (
                (10, 100, 100),
                (22, 255, 255),
            ),
        ),
        "yellow": (
            (
                (20, 100, 100),
                (35, 255, 255),
            ),
        ),
        "lime": (
            (
                (35, 80, 80),
                (55, 255, 255),
            ),
        ),
        "green": (
            (
                (45, 80, 60),
                (85, 255, 255),
            ),
        ),
        "teal": (
            (
                (80, 70, 60),
                (100, 255, 255),
            ),
        ),
        "cyan": (
            (
                (85, 80, 80),
                (100, 255, 255),
            ),
        ),
        "blue": (
            (
                (100, 80, 60),
                (130, 255, 255),
            ),
        ),
        "purple": (
            (
                (130, 70, 50),
                (155, 255, 255),
            ),
        ),
        "magenta": (
            (
                (145, 80, 70),
                (170, 255, 255),
            ),
        ),
        "pink": (
            (
                (160, 40, 100),
                (180, 255, 255),
            ),
        ),
        "white": (
            (
                (0, 0, 180),
                (180, 70, 255),
            ),
        ),
        "gray": (
            (
                (0, 0, 50),
                (180, 60, 190),
            ),
        ),
        "black": (
            (
                (0, 0, 0),
                (180, 255, 50),
            ),
        ),
    }

    def __init__(
        self,
        colors: str | Sequence[str] = "red",
        *,
        custom_ranges: Mapping[
            str,
            HSVRangeInput,
        ]
        | None = None,
        min_area: float = 500.0,
        enabled: bool = False,
    ) -> None:
        super().__init__(
            "color",
            enabled=enabled,
        )

        self._ranges = dict(self.DEFAULT_RANGES)
        self.colors: list[str] = []
        self.min_area = 0.0

        self.configure(
            colors,
            custom_ranges=custom_ranges,
            min_area=min_area,
        )

    def available_colors(
        self,
    ) -> tuple[str, ...]:
        return tuple(self._ranges)

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
                    "colors": list(self.colors),
                    "count": 0,
                    "counts": {color: 0 for color in self.colors},
                    "error": ("expected 3-channel image"),
                },
            )

        try:
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

        except cv2.error as exc:
            raise DetectorError(f"color detection failed: {exc}") from exc

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

        for lower, upper in self._ranges[color]:
            current = cv2.inRange(
                hsv,
                lower,
                upper,
            )

            mask = (
                current
                if mask is None
                else cv2.bitwise_or(
                    mask,
                    current,
                )
            )

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
        custom_ranges: Mapping[
            str,
            HSVRangeInput,
        ]
        | None = None,
        min_area: float | None = None,
    ) -> None:
        if custom_ranges is not None:
            self._ranges.update(_validate_custom_ranges(custom_ranges))

        if colors is not None:
            self.colors = _validate_colors(
                colors,
                supported=self._ranges,
            )

        if min_area is not None:
            self.min_area = _validate_min_area(min_area)

    def enable(
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
        self.configure(
            colors,
            custom_ranges=custom_ranges,
            min_area=min_area,
        )
        super().enable()
