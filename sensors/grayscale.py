from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Self

from betabox_robotics.hardware import ADC

from .exceptions import GrayscaleError
from .types import GrayscaleReading

if TYPE_CHECKING:
    from betabox_robotics.robots.config import GrayscaleConfig

class Grayscale:
    """
    Three-channel grayscale sensor.

    Channels are ordered left, middle, right.
    """

    LEFT = 0
    MIDDLE = 1
    RIGHT = 2

    REFERENCE_DEFAULT = (1000, 1000, 1000)

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

        selected_reference = (
            self.REFERENCE_DEFAULT
            if reference is None
            else reference
        )

        if len(selected_reference) != 3:
            raise GrayscaleError(
                "reference values must contain 3 values"
            )

        self._reference = tuple(
            int(value)
            for value in selected_reference
        )

        self._floor: tuple[float, float, float] | None = None
        self._line: tuple[float, float, float] | None = None
        self._closed = False

    @classmethod
    def default(cls, config: "GrayscaleConfig") -> "Grayscale":
        return cls(
            left=ADC(config.left),
            middle=ADC(config.middle),
            right=ADC(config.right),
            reference=config.reference,
        )

    def read(
        self,
        channel: int | None = None,
    ) -> list[int]:
        self._require_open()

        try:
            if channel is None:
                return [
                    adc.read()
                    for adc in self.channels
                ]

            self._validate_channel(channel)
            return [self.channels[channel].read()]

        except GrayscaleError:
            raise
        except Exception as exc:
            raise GrayscaleError(
                f"failed to read grayscale sensor: {exc}"
            ) from exc

    def reference(
        self,
        values: Sequence[int] | None = None,
    ) -> list[int]:
        self._require_open()
        if values is not None:
            if len(values) != 3:
                raise GrayscaleError(
                    "reference values must contain 3 values"
                )

            self._reference = tuple(
                int(value)
                for value in values
            )

        return list(self._reference)

    def set_calibration(
        self,
        floor: Sequence[float],
        line: Sequence[float],
    ) -> None:
        self._require_open()

        if len(floor) != 3 or len(line) != 3:
            raise GrayscaleError(
                "floor and line must each contain 3 values"
            )

        self._floor = (
            float(floor[0]),
            float(floor[1]),
            float(floor[2]),
        )
        self._line = (
            float(line[0]),
            float(line[1]),
            float(line[2]),
        )

    def get_calibration(
        self,
    ) -> tuple[
        tuple[float, float, float] | None,
        tuple[float, float, float] | None,
    ]:
        self._require_open()
        return self._floor, self._line

    def normalized(
        self,
        raw: Sequence[int] | None = None,
    ) -> list[float]:
        self._require_open()

        if self._floor is None or self._line is None:
            raise GrayscaleError(
                "calibration not set. Call set_calibration(floor, line) first."
            )

        values = raw if raw is not None else self.read()

        if len(values) != 3:
            raise GrayscaleError("raw values must contain 3 readings")

        normalized_values = []

        for index, value in enumerate(values):
            floor = self._floor[index]
            line = self._line[index]

            if line > floor:
                span = max(line - floor, 1e-6)
                normalized = (value - floor) / span
            else:
                span = max(floor - line, 1e-6)
                normalized = (floor - value) / span

            normalized = self._clamp(normalized, 0.0, 1.0)
            normalized_values.append(normalized)

        return normalized_values

    def status(
        self,
        raw: Sequence[int] | None = None,
        threshold: float = 0.5,
    ) -> list[int]:
        """
        Return 0 for floor and 1 for line.

        If floor/line calibration is available, normalized values are used.
        Otherwise, legacy reference thresholds are used.
        """

        if not 0.0 <= threshold <= 1.0:
            raise GrayscaleError(
                "threshold must be between 0.0 and 1.0"
            )

        if self._floor is not None and self._line is not None:
            return [1 if value > threshold else 0 for value in self.normalized(raw)]

        values = raw if raw is not None else self.read()

        if len(values) != 3:
            raise GrayscaleError("raw values must contain 3 readings")

        return [
            0 if value > self._reference[index] else 1
            for index, value in enumerate(values)
        ]

    def read_status(
        self,
        datas: Sequence[int] | None = None,
        threshold: float = 0.5,
    ) -> list[int]:
        """
        Compatibility alias for old API.
        """
        return self.status(raw=datas, threshold=threshold)

    def get_grayscale_normalized(self) -> list[float]:
        """
        Compatibility alias for old API.
        """
        return self.normalized()

    def reading(
        self,
        *,
        threshold: float = 0.5,
    ) -> GrayscaleReading:
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

        try:
            for adc in self.channels:
                adc.close()
        finally:
            self._closed = True

    def deinit(self) -> None:
        self.close()

    @property
    def closed(self) -> bool:
        return self._closed


    def _require_open(self) -> None:
        if self._closed:
            raise GrayscaleError("grayscale sensor is closed")

    def _validate_channel(self, channel: int) -> None:
        if channel not in (self.LEFT, self.MIDDLE, self.RIGHT):
            raise GrayscaleError(
                "channel must be Grayscale.LEFT, Grayscale.MIDDLE, or Grayscale.RIGHT"
            )

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
