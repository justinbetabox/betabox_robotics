from __future__ import annotations

import logging
import math
from enum import Enum
from time import sleep
from typing import ClassVar, Self

from .exceptions import HardwareError
from .pin import Pin
from .pwm import PWM


class MotorMode(Enum):
    PWM_DIR = 1
    PWM_PWM = 2


class MotorError(HardwareError):
    """Raised when a motor operation fails."""


class Motor:
    """
    Betabox DC motor abstraction.

    PWM_DIR uses one PWM channel and one digital direction pin.
    PWM_PWM uses two PWM channels, one for each direction.

    The Motor owns the devices passed to it and closes them when the
    motor is closed.
    """

    DEFAULT_FREQUENCY: ClassVar[float] = 100.0
    DEFAULT_MAX_STEP: ClassVar[float] = 5.0
    DEFAULT_STEP_DELAY: ClassVar[float] = 0.01

    def __init__(
        self,
        pwm: PWM,
        direction: Pin | PWM,
        *,
        reversed: bool = False,
        mode: MotorMode = MotorMode.PWM_DIR,
        frequency: float = DEFAULT_FREQUENCY,
        max_step: float = DEFAULT_MAX_STEP,
        step_delay: float = DEFAULT_STEP_DELAY,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        if not isinstance(mode, MotorMode):
            raise TypeError("mode must be MotorMode.PWM_DIR or MotorMode.PWM_PWM")

        if not isinstance(reversed, bool):
            raise TypeError("reversed must be a boolean")

        frequency_value = self._require_finite_number(
            frequency,
            name="frequency",
        )
        max_step_value = self._require_finite_number(
            max_step,
            name="max_step",
        )
        step_delay_value = self._require_finite_number(
            step_delay,
            name="step_delay",
        )

        if frequency_value <= 0:
            raise MotorError("frequency must be greater than 0")

        if max_step_value <= 0:
            raise MotorError("max_step must be greater than 0")

        if step_delay_value < 0:
            raise MotorError("step_delay cannot be negative")

        self.mode = mode
        self.reversed = reversed
        self.frequency = frequency_value
        self.max_step = max_step_value
        self.step_delay = step_delay_value

        self._speed = 0.0
        self._closed = False

        self.pwm: PWM
        self.direction: Pin
        self.pwm_a: PWM
        self.pwm_b: PWM

        if mode is MotorMode.PWM_DIR:
            if not isinstance(pwm, PWM):
                raise TypeError("pwm must be a PWM instance")

            if not isinstance(direction, Pin):
                raise TypeError(
                    "direction must be a Pin instance when using PWM_DIR mode"
                )

            self.pwm = pwm
            self.direction = direction

        else:
            if not isinstance(pwm, PWM):
                raise TypeError("pwm must be a PWM instance")

            if not isinstance(direction, PWM):
                raise TypeError(
                    "direction must be a PWM instance when using PWM_PWM mode"
                )

            self.pwm_a = pwm
            self.pwm_b = direction

        try:
            self._initialize_outputs()
        except BaseException:
            try:
                self._close_devices()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as cleanup_error:
                self.logger.warning(
                    "Motor cleanup failed after construction error: %s",
                    cleanup_error,
                )
            finally:
                self._speed = 0.0
                self._closed = True

            raise

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
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise MotorError("Motor is closed")

    def _initialize_outputs(self) -> None:
        if self.mode is MotorMode.PWM_DIR:
            self.pwm.set_frequency(self.frequency)
            self.pwm.set_duty_cycle(0)
            self.direction.write(False)
            return

        self.pwm_a.set_frequency(self.frequency)
        self.pwm_a.set_duty_cycle(0)

        self.pwm_b.set_frequency(self.frequency)
        self.pwm_b.set_duty_cycle(0)

    def set_speed(
        self,
        speed: float,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        value = self._require_finite_number(
            speed,
            name="speed",
        )

        if not isinstance(smooth, bool):
            raise TypeError("smooth must be a boolean")

        target = self._clamp(
            value,
            -100.0,
            100.0,
        )

        if not smooth:
            self._set_speed_immediate(target)
            return

        current = self._speed

        while abs(target - current) > self.max_step:
            if target > current:
                current += self.max_step
            else:
                current -= self.max_step

            self._set_speed_immediate(current)

            if self.step_delay > 0:
                sleep(self.step_delay)

        self._set_speed_immediate(target)

    def get_speed(self) -> float:
        return self._speed

    def stop(self) -> None:
        """Ramp the motor down to a controlled stop."""

        self.set_speed(
            0,
            smooth=True,
        )

    def emergency_stop(self) -> None:
        """Immediately remove motor drive output."""

        self._require_open()
        self._set_speed_immediate(0)

    def _effective_direction(
        self,
        speed: float,
    ) -> bool:
        direction = speed > 0

        if self.reversed:
            direction = not direction

        return direction

    def _set_speed_immediate(
        self,
        speed: float,
    ) -> None:
        self._require_open()

        value = self._clamp(
            speed,
            -100.0,
            100.0,
        )

        direction = self._effective_direction(value)
        duty = abs(value)

        if self.mode is MotorMode.PWM_DIR:
            if value == 0:
                # Preserve the current direction and remove drive output.
                self.pwm.set_duty_cycle(0)
            else:
                previous_direction = self._effective_direction(self._speed)

                if self._speed != 0 and direction != previous_direction:
                    # De-energize before reversing the direction pin.
                    self.pwm.set_duty_cycle(0)

                self.direction.write(direction)
                self.pwm.set_duty_cycle(duty)

        else:
            if value == 0:
                self.pwm_a.set_duty_cycle(0)
                self.pwm_b.set_duty_cycle(0)

            elif direction:
                # Disable the opposite direction before applying output.
                self.pwm_b.set_duty_cycle(0)
                self.pwm_a.set_duty_cycle(duty)

            else:
                self.pwm_a.set_duty_cycle(0)
                self.pwm_b.set_duty_cycle(duty)

        self._speed = value

    def forward(
        self,
        speed: float,
    ) -> None:
        value = self._require_finite_number(
            speed,
            name="speed",
        )

        self.set_speed(abs(value))

    def backward(
        self,
        speed: float,
    ) -> None:
        value = self._require_finite_number(
            speed,
            name="speed",
        )

        self.set_speed(-abs(value))

    def speed(
        self,
        speed: float | None = None,
    ) -> float | None:
        if speed is None:
            return self.get_speed()

        self.set_speed(speed)
        return None

    def set_reversed(
        self,
        reversed: bool,
    ) -> None:
        self._require_open()

        if not isinstance(reversed, bool):
            raise TypeError("reversed must be a boolean")

        if self._speed != 0:
            raise MotorError("motor must be stopped before changing reversed state")

        self.reversed = reversed

    def _close_devices(self) -> None:
        if self.mode is MotorMode.PWM_DIR:
            try:
                self.pwm.set_duty_cycle(0)
            finally:
                try:
                    self.pwm.close()
                finally:
                    self.direction.close()

            return

        try:
            self.pwm_a.set_duty_cycle(0)
        finally:
            try:
                self.pwm_b.set_duty_cycle(0)
            finally:
                try:
                    self.pwm_a.close()
                finally:
                    self.pwm_b.close()

    def close(self) -> None:
        if self._closed:
            return

        try:
            self._close_devices()
        finally:
            self._speed = 0.0
            self._closed = True

    def deinit(self) -> None:
        self.close()

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
