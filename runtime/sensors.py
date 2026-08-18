from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING, Self

from betabox_robotics.calibration import RobotCalibration
from betabox_robotics.robots.config import (
    BatteryConfig,
    GrayscaleConfig,
)
from betabox_robotics.sensors import (
    BatteryReading,
    BatteryState,
    GrayscaleReading,
    SensorsStatus,
    UltrasonicReading,
)

from .client import RobotRuntimeClient

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        BatteryConfig,
        GrayscaleConfig,
    )


class RuntimeBattery:
    """Battery sensor backed by the centralized robot runtime."""

    client: RobotRuntimeClient
    low_voltage: float
    critical_voltage: float

    _closed: bool

    def __init__(
        self,
        client: RobotRuntimeClient,
        config: BatteryConfig,
    ) -> None:
        self.client = client
        self.low_voltage = float(config.low_voltage)
        self.critical_voltage = float(config.critical_voltage)
        self._closed = False

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    def _require_open(
        self,
    ) -> None:
        if self._closed:
            raise RuntimeError("runtime battery sensor is closed")

    def voltage(
        self,
    ) -> float:
        self._require_open()

        return self.client.battery_voltage()

    def read(
        self,
    ) -> float:
        return self.voltage()

    def _state_for_voltage(
        self,
        voltage: float,
    ) -> BatteryState:
        if voltage <= self.critical_voltage:
            return BatteryState.CRITICAL

        if voltage <= self.low_voltage:
            return BatteryState.LOW

        return BatteryState.OK

    def status(
        self,
    ) -> BatteryState:
        voltage = self.voltage()

        return self._state_for_voltage(
            voltage,
        )

    def reading(
        self,
    ) -> BatteryReading:
        voltage = self.voltage()

        return BatteryReading(
            voltage=voltage,
            state=self._state_for_voltage(
                voltage,
            ),
        )

    def is_low(
        self,
    ) -> bool:
        return self.reading().low

    def is_critical(
        self,
    ) -> bool:
        return self.reading().critical

    def close(
        self,
    ) -> None:
        self._closed = True

    def deinit(
        self,
    ) -> None:
        self.close()

    def __enter__(
        self,
    ) -> Self:
        self._require_open()

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()


class RuntimeUltrasonic:
    """Ultrasonic sensor backed by the centralized robot runtime."""

    client: RobotRuntimeClient

    _closed: bool

    def __init__(
        self,
        client: RobotRuntimeClient,
    ) -> None:
        self.client = client
        self._closed = False

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    def _require_open(
        self,
    ) -> None:
        if self._closed:
            raise RuntimeError("runtime ultrasonic sensor is closed")

    @staticmethod
    def _validate_samples(
        samples: object,
    ) -> int:
        if isinstance(samples, bool) or not isinstance(
            samples,
            int,
        ):
            raise TypeError("samples must be an integer")

        if samples <= 0:
            raise ValueError("samples must be greater than 0")

        return samples

    def distance(
        self,
        samples: int = 10,
    ) -> float:
        self._require_open()

        sample_count = self._validate_samples(
            samples,
        )

        return self.client.ultrasonic_distance(
            samples=sample_count,
        )

    def reading(
        self,
        samples: int = 10,
    ) -> UltrasonicReading:
        sample_count = self._validate_samples(
            samples,
        )

        return UltrasonicReading(
            distance_cm=self.distance(
                samples=sample_count,
            ),
            samples_requested=sample_count,
        )

    def close(
        self,
    ) -> None:
        self._closed = True

    def deinit(
        self,
    ) -> None:
        self.close()

    def __enter__(
        self,
    ) -> Self:
        self._require_open()

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()


class RuntimeGrayscale:
    """Grayscale sensor backed by the centralized robot runtime."""

    client: RobotRuntimeClient

    _reference: tuple[int, int, int]
    _floor: tuple[float, float, float] | None
    _line: tuple[float, float, float] | None
    _closed: bool

    def __init__(
        self,
        client: RobotRuntimeClient,
        config: GrayscaleConfig,
        *,
        calibration: RobotCalibration | None = None,
    ) -> None:
        self.client = client

        self._reference = (
            int(config.reference[0]),
            int(config.reference[1]),
            int(config.reference[2]),
        )

        self._floor = None
        self._line = None
        self._closed = False

        if calibration is not None:
            grayscale = calibration.grayscale

            if grayscale.calibrated:
                floor = grayscale.floor
                line = grayscale.line

                if floor is None or line is None:
                    raise ValueError(
                        "calibrated grayscale data must contain floor and line values"
                    )

                self.set_calibration(
                    floor,
                    line,
                )

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    def _require_open(
        self,
    ) -> None:
        if self._closed:
            raise RuntimeError("runtime grayscale sensor is closed")

    @staticmethod
    def _require_number(
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
    def _triplet(
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

        if len(values) != 3:
            raise ValueError(f"{name} must contain 3 values")

        return (
            cls._require_number(
                values[0],
                name=f"{name}[0]",
            ),
            cls._require_number(
                values[1],
                name=f"{name}[1]",
            ),
            cls._require_number(
                values[2],
                name=f"{name}[2]",
            ),
        )

    def read(
        self,
    ) -> list[int]:
        self._require_open()

        values = self.client.grayscale_values()

        return [
            values[0],
            values[1],
            values[2],
        ]

    def set_calibration(
        self,
        floor: Sequence[float],
        line: Sequence[float],
    ) -> None:
        self._require_open()

        floor_values = self._triplet(
            floor,
            name="floor",
        )
        line_values = self._triplet(
            line,
            name="line",
        )

        for index in range(3):
            if floor_values[index] == line_values[index]:
                raise ValueError(
                    f"floor and line calibration values must differ for channel {index}"
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
            raise RuntimeError("calibration not set")

        values = self._triplet(
            self.read() if raw is None else raw,
            name="raw values",
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
                max(
                    0.0,
                    min(
                        1.0,
                        normalized,
                    ),
                )
            )

        return normalized_values

    def status(
        self,
        raw: Sequence[int | float] | None = None,
        threshold: float = 0.5,
    ) -> list[int]:
        self._require_open()

        threshold_value = self._require_number(
            threshold,
            name="threshold",
        )

        if not 0.0 <= threshold_value <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

        if self._floor is not None and self._line is not None:
            return [
                1 if value > threshold_value else 0 for value in self.normalized(raw)
            ]

        values = self._triplet(
            self.read() if raw is None else raw,
            name="raw values",
        )

        return [
            0 if value > self._reference[index] else 1
            for index, value in enumerate(values)
        ]

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
            normalized = self.normalized(
                raw_values,
            )

            normalized_values = (
                normalized[0],
                normalized[1],
                normalized[2],
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

    def close(
        self,
    ) -> None:
        self._closed = True

    def deinit(
        self,
    ) -> None:
        self.close()

    def __enter__(
        self,
    ) -> Self:
        self._require_open()

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()


class RuntimeSensors:
    """Combined sensors backed by the centralized robot runtime."""

    ultrasonic: RuntimeUltrasonic
    grayscale: RuntimeGrayscale
    battery: RuntimeBattery

    _closed: bool

    def __init__(
        self,
        client: RobotRuntimeClient,
        *,
        battery_config: BatteryConfig,
        grayscale_config: GrayscaleConfig,
        calibration: RobotCalibration | None = None,
    ) -> None:
        self.ultrasonic = RuntimeUltrasonic(
            client,
        )
        self.grayscale = RuntimeGrayscale(
            client,
            grayscale_config,
            calibration=calibration,
        )
        self.battery = RuntimeBattery(
            client,
            battery_config,
        )

        self._closed = False

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    def status(
        self,
    ) -> SensorsStatus:
        return SensorsStatus(
            ultrasonic_closed=self.ultrasonic.closed,
            grayscale_closed=self.grayscale.closed,
            battery_closed=self.battery.closed,
            closed=self.closed,
        )

    def close(
        self,
    ) -> None:
        if self._closed:
            return

        try:
            self.battery.close()
        finally:
            try:
                self.grayscale.close()
            finally:
                self.ultrasonic.close()
                self._closed = True

    def deinit(
        self,
    ) -> None:
        self.close()

    def __enter__(
        self,
    ) -> Self:
        if self._closed:
            raise RuntimeError("runtime sensors subsystem is closed")

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
