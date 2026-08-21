from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar, Self

from betabox_robotics.calibration import (
    GRAYSCALE_MIN_CALIBRATION_SPAN,
)
from betabox_robotics.hardware import (
    ADC,
    HardwareError,
)

from .exceptions import GrayscaleError
from .types import GrayscaleReading

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        GrayscaleConfig,
    )


class Grayscale:
    """
    Three-channel grayscale sensor.

    Channels are ordered left, middle, right. The Grayscale subsystem
    owns all three ADC objects and closes them when it is closed.
    """

    LEFT: ClassVar[int] = 0
    MIDDLE: ClassVar[int] = 1
    RIGHT: ClassVar[int] = 2

    CHANNEL_COUNT: ClassVar[int] = 3
    REFERENCE_DEFAULT: ClassVar[tuple[int, int, int]] = (
        1000,
        1000,
        1000,
    )

    channels: tuple[ADC, ADC, ADC]

    _reference: tuple[int, int, int]
    _floor: tuple[float, float, float] | None
    _line: tuple[float, float, float] | None
    _closed: bool

    def __init__(
        self,
        left: ADC,
        middle: ADC,
        right: ADC,
        reference: Sequence[int] | None = None,
    ) -> None:
        self.channels = (
            left,
            middle,
            right,
        )

        selected_reference = self.REFERENCE_DEFAULT if reference is None else reference

        self._reference = self._validated_reference(selected_reference)

        self._floor = None
        self._line = None
        self._closed = False

    @classmethod
    def default(
        cls,
        config: GrayscaleConfig,
    ) -> Self:
        left: ADC | None = None
        middle: ADC | None = None
        right: ADC | None = None

        try:
            left = ADC(config.left)

            middle = ADC(config.middle)

            right = ADC(config.right)

            return cls(
                left=left,
                middle=middle,
                right=right,
                reference=config.reference,
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            # Close in reverse construction order.
            for adc in (
                right,
                middle,
                left,
            ):
                if adc is None:
                    continue

                try:
                    adc.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            raise

    @staticmethod
    def _require_finite_number(
        value: object,
        *,
        name: str,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            int | float,
        ):
            raise TypeError(f"{name} must be a number")

        result = float(value)

        if not math.isfinite(result):
            raise ValueError(f"{name} must be finite")

        return result

    @classmethod
    def _validated_reference(
        cls,
        values: Sequence[int],
    ) -> tuple[int, int, int]:
        if isinstance(
            values,
            str | bytes | bytearray,
        ):
            raise TypeError("reference values must be a sequence of integers")

        if len(values) != cls.CHANNEL_COUNT:
            raise GrayscaleError("reference values must contain 3 values")

        validated: list[int] = []

        for index, value in enumerate(values):
            if not 0 <= value <= ADC.MAX_VALUE:
                raise GrayscaleError(
                    f"reference value {index} must be between 0 and {ADC.MAX_VALUE}"
                )

            validated.append(value)

        return (
            validated[0],
            validated[1],
            validated[2],
        )

    @classmethod
    def _validated_triplet(
        cls,
        values: Sequence[int | float],
        *,
        name: str,
    ) -> tuple[float, float, float]:
        if isinstance(
            values,
            str | bytes | bytearray,
        ):
            raise TypeError(f"{name} must be a sequence of numbers")

        if len(values) != cls.CHANNEL_COUNT:
            raise GrayscaleError(f"{name} must contain 3 values")

        validated = [
            cls._require_finite_number(
                value,
                name=f"{name}[{index}]",
            )
            for index, value in enumerate(values)
        ]

        return (
            validated[0],
            validated[1],
            validated[2],
        )

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise GrayscaleError("grayscale sensor is closed")

    def read(
        self,
        channel: int | None = None,
    ) -> list[int]:
        self._require_open()

        try:
            if channel is None:
                return [adc.read() for adc in self.channels]

            channel_index = self._validate_channel(channel)

            return [self.channels[channel_index].read()]

        except (
            HardwareError,
            OSError,
            RuntimeError,
        ) as exc:
            raise GrayscaleError(f"failed to read grayscale sensor: {exc}") from exc

    def reference(
        self,
        values: Sequence[int] | None = None,
    ) -> list[int]:
        self._require_open()

        if values is not None:
            self._reference = self._validated_reference(values)

        return list(self._reference)

    def set_calibration(
        self,
        floor: Sequence[float],
        line: Sequence[float],
    ) -> None:
        self._require_open()

        floor_values = self._validated_triplet(
            floor,
            name="floor",
        )

        line_values = self._validated_triplet(
            line,
            name="line",
        )

        for index, (
            floor_value,
            line_value,
        ) in enumerate(
            zip(
                floor_values,
                line_values,
                strict=True,
            )
        ):
            span = abs(floor_value - line_value)

            if span < GRAYSCALE_MIN_CALIBRATION_SPAN:
                raise GrayscaleError(
                    "floor and line calibration values "
                    + "must differ by at least "
                    + f"{GRAYSCALE_MIN_CALIBRATION_SPAN:g} "
                    + f"for channel {index}"
                )

        self._floor = floor_values
        self._line = line_values

    def get_calibration(
        self,
    ) -> tuple[
        tuple[float, float, float] | None,
        tuple[float, float, float] | None,
    ]:
        self._require_open()

        return (
            self._floor,
            self._line,
        )

    def normalized(
        self,
        raw: Sequence[int | float] | None = None,
    ) -> list[float]:
        self._require_open()

        floor = self._floor
        line = self._line

        if floor is None or line is None:
            raise GrayscaleError(
                "calibration not set. Call set_calibration(floor, line) first."
            )

        values = (
            self._validated_triplet(
                raw,
                name="raw values",
            )
            if raw is not None
            else self._validated_triplet(
                self.read(),
                name="raw values",
            )
        )

        normalized_values: list[float] = []

        for index, value in enumerate(values):
            floor_value = floor[index]
            line_value = line[index]

            if line_value > floor_value:
                normalized = (value - floor_value) / (line_value - floor_value)
            else:
                normalized = (floor_value - value) / (floor_value - line_value)

            normalized_values.append(
                self._clamp(
                    normalized,
                    0.0,
                    1.0,
                )
            )

        return normalized_values

    def status(
        self,
        raw: Sequence[int | float] | None = None,
        threshold: float = 0.5,
    ) -> list[int]:
        """
        Return 0 for floor and 1 for line.

        When floor/line calibration is available, normalized values are
        used. Otherwise, the legacy reference thresholds are used.
        """

        self._require_open()

        threshold_value = self._require_finite_number(
            threshold,
            name="threshold",
        )

        if not 0.0 <= threshold_value <= 1.0:
            raise GrayscaleError("threshold must be between 0.0 and 1.0")

        if self._floor is not None and self._line is not None:
            return [
                1 if value > threshold_value else 0 for value in self.normalized(raw)
            ]

        values = (
            self._validated_triplet(
                raw,
                name="raw values",
            )
            if raw is not None
            else self._validated_triplet(
                self.read(),
                name="raw values",
            )
        )

        return [
            (0 if value > self._reference[index] else 1)
            for index, value in enumerate(values)
        ]

    def read_status(
        self,
        datas: Sequence[int | float] | None = None,
        threshold: float = 0.5,
    ) -> list[int]:
        """Compatibility alias for the legacy API."""

        return self.status(
            raw=datas,
            threshold=threshold,
        )

    def get_grayscale_normalized(
        self,
    ) -> list[float]:
        """Compatibility alias for the legacy API."""

        return self.normalized()

    def reading(
        self,
        *,
        threshold: float = 0.5,
    ) -> GrayscaleReading:
        self._require_open()

        raw_values = self.read()

        status_values = self.status(
            raw=raw_values,
            threshold=threshold,
        )

        normalized_values: tuple[float, float, float] | None = None

        if self._floor is not None and self._line is not None:
            values = self.normalized(raw_values)

            normalized_values = (
                values[0],
                values[1],
                values[2],
            )

        return GrayscaleReading(
            raw=(
                raw_values[0],
                raw_values[1],
                raw_values[2],
            ),
            status=(
                status_values[0],
                status_values[1],
                status_values[2],
            ),
            normalized=normalized_values,
        )

    def close(self) -> None:
        if self._closed:
            return

        first_error: HardwareError | OSError | RuntimeError | None = None

        try:
            # Close in reverse construction order.
            for adc in reversed(self.channels):
                try:
                    adc.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ) as exc:
                    if first_error is None:
                        first_error = exc

        finally:
            self._closed = True

        if first_error is not None:
            raise first_error

    def deinit(self) -> None:
        self.close()

    @classmethod
    def _validate_channel(
        cls,
        channel: object,
    ) -> int:
        if isinstance(channel, bool) or not isinstance(
            channel,
            int,
        ):
            raise TypeError("channel must be an integer")

        if channel not in (
            cls.LEFT,
            cls.MIDDLE,
            cls.RIGHT,
        ):
            raise GrayscaleError(
                "channel must be Grayscale.LEFT, Grayscale.MIDDLE, or Grayscale.RIGHT"
            )

        return channel

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
