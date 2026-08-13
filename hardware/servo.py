from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from time import sleep
from typing import ClassVar, Self

from .board import PWMChannel
from .exceptions import HardwareError
from .i2c import I2C
from .pwm import PWM


class ServoError(HardwareError):
    """Raised when a servo operation fails."""


def map_range(
    value: float,
    in_min: float,
    in_max: float,
    out_min: float,
    out_max: float,
) -> float:
    if in_min == in_max:
        raise ValueError("input range cannot have equal minimum and maximum")

    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class Servo:
    """
    Betabox servo abstraction.

    Public angles are in degrees. Default range is -90 to 90.
    """

    logger: logging.Logger

    min_angle: float
    max_angle: float
    offset: float
    max_step: float
    step_delay: float

    _angle: float | None
    _physical_angle: float | None
    _pwm: PWM | None

    MIN_PULSE_US: ClassVar[float] = 500.0
    MAX_PULSE_US: ClassVar[float] = 2500.0
    FREQUENCY_HZ: ClassVar[float] = 50.0
    PERIOD: ClassVar[int] = 4095

    DEFAULT_MAX_STEP: ClassVar[float] = 2.0
    DEFAULT_STEP_DELAY: ClassVar[float] = 0.01

    def __init__(
        self,
        channel: int | str | PWMChannel,
        address: int | Sequence[int] | None = None,
        bus: I2C | None = None,
        min_angle: float = -90,
        max_angle: float = 90,
        offset: float = 0,
        max_step: float = DEFAULT_MAX_STEP,
        step_delay: float = DEFAULT_STEP_DELAY,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        minimum = self._require_finite_number(
            min_angle,
            name="min_angle",
        )
        maximum = self._require_finite_number(
            max_angle,
            name="max_angle",
        )
        offset_value = self._require_finite_number(
            offset,
            name="offset",
        )
        max_step_value = self._require_finite_number(
            max_step,
            name="max_step",
        )
        step_delay_value = self._require_finite_number(
            step_delay,
            name="step_delay",
        )

        if not -90.0 <= minimum <= 90.0:
            raise ServoError("min_angle must be between -90 and 90")

        if not -90.0 <= maximum <= 90.0:
            raise ServoError("max_angle must be between -90 and 90")

        if minimum >= maximum:
            raise ServoError("min_angle must be less than max_angle")

        if max_step_value <= 0:
            raise ServoError("max_step must be greater than 0")

        if step_delay_value < 0:
            raise ServoError("step_delay cannot be negative")

        self.min_angle = minimum
        self.max_angle = maximum
        self.offset = offset_value
        self.max_step = max_step_value
        self.step_delay = step_delay_value

        self._angle = None
        self._physical_angle = None
        self._pwm = None

        try:
            self._pwm = PWM(
                channel,
                address=address,
                bus=bus,
            )

            self.pwm.set_period(self.PERIOD)

            prescaler = self.pwm.CLOCK / self.FREQUENCY_HZ / self.PERIOD

            self.pwm.set_prescaler(prescaler)

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            try:
                self.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as cleanup_error:
                self.logger.warning(
                    "Servo cleanup failed after construction error: %s",
                    cleanup_error,
                )

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

    @property
    def closed(self) -> bool:
        return self._pwm is None

    @property
    def pwm(self) -> PWM:
        pwm = self._pwm

        if pwm is None:
            raise ServoError("Servo PWM has been closed")

        return pwm

    def move_to(
        self,
        angle: float,
        smooth: bool = True,
    ) -> None:
        logical_target = self._require_finite_number(
            angle,
            name="angle",
        )
        physical_target = self._logical_to_physical(logical_target)

        if not smooth or self._physical_angle is None:
            self._move_immediate(physical_target)
            return

        current_physical = self._physical_angle

        while abs(physical_target - current_physical) > self.max_step:
            if physical_target > current_physical:
                current_physical += self.max_step
            else:
                current_physical -= self.max_step

            self._write_physical_angle(current_physical)

            if self.step_delay > 0:
                sleep(self.step_delay)

        self._move_immediate(physical_target)

    def _logical_to_physical(
        self,
        angle: float,
    ) -> float:
        return self._clamp(
            angle + self.offset,
            self.min_angle,
            self.max_angle,
        )

    def _write_physical_angle(
        self,
        angle: float,
    ) -> None:
        pulse_us = self._angle_to_pulse_us(angle)

        self.logger.debug(
            "Servo physical_angle=%s pulse_us=%s",
            angle,
            pulse_us,
        )

        self.set_pulse_width_us(pulse_us)

        self._physical_angle = angle

    def _physical_to_logical(
        self,
        angle: float,
    ) -> float:
        return angle - self.offset

    def _move_immediate(
        self,
        physical_angle: float,
    ) -> None:
        self._write_physical_angle(physical_angle)

        self._angle = self._physical_to_logical(physical_angle)

    def center(self) -> None:
        self.move_to(0)

    def min(self) -> None:
        self.move_to(self.min_angle - self.offset)

    def max(self) -> None:
        self.move_to(self.max_angle - self.offset)

    def set_pulse_width_us(
        self,
        pulse_us: float,
    ) -> None:
        value = self._require_finite_number(
            pulse_us,
            name="pulse_us",
        )

        clamped = self._clamp(
            value,
            self.MIN_PULSE_US,
            self.MAX_PULSE_US,
        )

        duty_fraction = clamped / 20_000.0

        pwm_value = int(duty_fraction * self.PERIOD)

        self.logger.debug(
            "Servo pulse_us=%s pwm_value=%s",
            clamped,
            pwm_value,
        )

        self.pwm.set_pulse_width(pwm_value)

    @property
    def physical_angle(
        self,
    ) -> float | None:
        return self._physical_angle

    def get_angle(
        self,
    ) -> float | None:
        return self._angle

    @staticmethod
    def _angle_to_pulse_us(
        angle: float,
    ) -> float:
        return map_range(
            angle,
            -90.0,
            90.0,
            Servo.MIN_PULSE_US,
            Servo.MAX_PULSE_US,
        )

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

    # Compatibility aliases

    def angle(
        self,
        angle: float | None = None,
    ) -> float | None:
        if angle is None:
            return self.get_angle()

        self.move_to(angle)
        return None

    def pulse_width_time(
        self,
        pulse_width_time: float,
    ) -> None:
        self.set_pulse_width_us(pulse_width_time)

    def close(self) -> None:
        pwm = self._pwm

        try:
            if pwm is not None:
                pwm.close()
        finally:
            self._pwm = None
            self._angle = None
            self._physical_angle = None

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        if self.closed:
            raise ServoError("Cannot enter a closed Servo")

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
