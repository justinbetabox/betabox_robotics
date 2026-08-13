from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import ClassVar, TypeAlias, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from typing_extensions import override

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
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple of three integers")

    values = cast(
        tuple[object, ...],
        value,
    )

    if len(values) != 3:
        raise TypeError(f"{name} must be a tuple of three integers")

    hue = values[0]
    saturation = values[1]
    brightness = values[2]

    if (
        isinstance(hue, bool)
        or not isinstance(hue, int)
        or isinstance(saturation, bool)
        or not isinstance(saturation, int)
        or isinstance(brightness, bool)
        or not isinstance(brightness, int)
    ):
        raise TypeError(f"{name} must contain three integers")

    if not 0 <= hue <= 180:
        raise ValueError(f"{name} hue must be between 0 and 180")

    if not 0 <= saturation <= 255:
        raise ValueError(f"{name} saturation must be between 0 and 255")

    if not 0 <= brightness <= 255:
        raise ValueError(f"{name} brightness must be between 0 and 255")

    return (
        hue,
        saturation,
        brightness,
    )


def _validate_hsv_range(
    value: object,
    *,
    name: str,
) -> HSVRange:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must contain lower and upper HSV values")

    values = cast(
        tuple[object, ...],
        value,
    )

    if len(values) != 2:
        raise TypeError(f"{name} must contain lower and upper HSV values")

    lower = _validate_hsv_value(
        values[0],
        name=f"{name} lower value",
    )

    upper = _validate_hsv_value(
        values[1],
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

    return (
        lower,
        upper,
    )


def _is_single_hsv_range(
    value: object,
) -> bool:
    if not isinstance(value, tuple):
        return False

    values = cast(
        tuple[object, ...],
        value,
    )

    if len(values) != 2:
        return False

    for bound in values:
        if not isinstance(bound, tuple):
            return False

        bound_values = cast(
            tuple[object, ...],
            bound,
        )

        if len(bound_values) != 3:
            return False

    return True


def _validate_custom_ranges(
    value: object,
) -> dict[str, tuple[HSVRange, ...]]:
    if not isinstance(value, Mapping):
        raise TypeError("custom_ranges must be a mapping")

    mapping = cast(
        Mapping[object, object],
        value,
    )

    validated: dict[str, tuple[HSVRange, ...]] = {}

    for raw_name, raw_ranges in mapping.items():
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
    else:
        raw_colors = list(value)

    if not raw_colors:
        raise ValueError("at least one color is required")

    colors = [color.strip().casefold() for color in raw_colors]

    if any(not color for color in colors):
        raise ValueError("color names cannot be empty")

    unsupported = [color for color in colors if color not in supported]

    if unsupported:
        raise ValueError("unsupported color(s): " + ", ".join(unsupported))

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

    _ranges: dict[str, tuple[HSVRange, ...]]
    colors: list[str]
    min_area: float

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
        self.colors = []
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

    @override
    def detect(
        self,
        frame: Frame,
    ) -> Metadata:

        image = frame.image

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
            hsv = cast(
                NDArray[np.uint8],
                cast(
                    object,
                    cv2.cvtColor(
                        image,
                        cv2.COLOR_RGB2HSV,
                    ),
                ),
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
            key=self._detection_area,
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

    @staticmethod
    def _detection_area(
        detection: Detection,
    ) -> float:
        area = detection.data.get(
            "area",
            0.0,
        )

        if isinstance(area, bool) or not isinstance(
            area,
            int | float,
        ):
            raise DetectorError("color detection returned an invalid area")

        return float(area)

    def _detect_color(
        self,
        hsv: NDArray[np.uint8],
        color: str,
    ) -> list[Detection]:
        mask: NDArray[np.uint8] | None = None

        for lower, upper in self._ranges[color]:
            lower_array: NDArray[np.uint8] = np.array(
                lower,
                dtype=np.uint8,
            )

            upper_array: NDArray[np.uint8] = np.array(
                upper,
                dtype=np.uint8,
            )

            current = cast(
                NDArray[np.uint8],
                cast(
                    object,
                    cv2.inRange(
                        hsv,
                        lower_array,
                        upper_array,
                    ),
                ),
            )

            if mask is None:
                mask = current
            else:
                mask = cast(
                    NDArray[np.uint8],
                    cast(
                        object,
                        cv2.bitwise_or(
                            mask,
                            current,
                        ),
                    ),
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

    @override
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
