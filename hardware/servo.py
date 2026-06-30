import logging
from time import sleep
from typing import List, Optional, Union

from .board import PWMChannel
from .exceptions import HardwareError
from .i2c import I2C
from .pwm import PWM


class ServoError(HardwareError):
    """Raised when a servo operation fails."""


def map_range(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class Servo:
    """
    Betabox servo abstraction.

    Public angles are in degrees. Default range is -90 to 90.
    """

    MIN_PULSE_US = 500
    MAX_PULSE_US = 2500
    FREQUENCY_HZ = 50
    PERIOD = 4095
    DEFAULT_MAX_STEP = 2.0
    DEFAULT_STEP_DELAY = 0.01

    def __init__(
        self,
        channel: Union[int, str, PWMChannel],
        address: Optional[Union[int, List[int]]] = None,
        bus: Optional[I2C] = None,
        min_angle: float = -90,
        max_angle: float = 90,
        offset: float = 0,
        max_step: float = DEFAULT_MAX_STEP,
        step_delay: float = DEFAULT_STEP_DELAY,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        if min_angle >= max_angle:
            raise ServoError("min_angle must be less than max_angle")

        self.min_angle = float(min_angle)
        self.max_angle = float(max_angle)
        self.offset = float(offset)

        self._angle: Optional[float] = None

        if max_step <= 0:
            raise ServoError("max_step must be greater than 0")
        if step_delay < 0:
            raise ServoError("step_delay cannot be negative")

        self.max_step = float(max_step)
        self.step_delay = float(step_delay)

        self._pwm: Optional[PWM] = PWM(channel, address=address, bus=bus)

        self.pwm.set_period(self.PERIOD)
        prescaler = self.pwm.CLOCK / self.FREQUENCY_HZ / self.PERIOD
        self.pwm.set_prescaler(prescaler)

    @property
    def pwm(self) -> PWM:
        if self._pwm is None:
            raise ServoError("Servo PWM has been closed")
        return self._pwm

    def move_to(self, angle: float, smooth: bool = True) -> None:
        if not isinstance(angle, (int, float)):
            raise ServoError(f"angle must be int or float, not {type(angle)}")

        requested_angle = float(angle)
        calibrated_angle = requested_angle + self.offset
        target_angle = self._clamp(calibrated_angle, self.min_angle, self.max_angle)

        if not smooth or self._angle is None:
            self._move_immediate(target_angle)
            return

        current = self._angle

        while abs(target_angle - current) > self.max_step:
            if target_angle > current:
                current += self.max_step
            else:
                current -= self.max_step

            self._move_immediate(current)

            if self.step_delay:
                sleep(self.step_delay)

        self._move_immediate(target_angle)

    def _move_immediate(self, angle: float) -> None:
        pulse_us = self._angle_to_pulse_us(angle)

        self.logger.debug(
            "Servo move angle=%s pulse_us=%s",
            angle,
            pulse_us,
        )

        self.set_pulse_width_us(pulse_us)
        self._angle = angle

    def center(self) -> None:
        self.move_to(0)

    def min(self) -> None:
        self.move_to(self.min_angle)

    def max(self) -> None:
        self.move_to(self.max_angle)

    def set_pulse_width_us(self, pulse_us: float) -> None:
        pulse_us = self._clamp(pulse_us, self.MIN_PULSE_US, self.MAX_PULSE_US)

        duty_fraction = pulse_us / 20_000.0
        pwm_value = int(duty_fraction * self.PERIOD)

        self.logger.debug(
            "Servo pulse_us=%s pwm_value=%s",
            pulse_us,
            pwm_value,
        )

        self.pwm.set_pulse_width(pwm_value)

    def get_angle(self) -> Optional[float]:
        return self._angle

    def _angle_to_pulse_us(self, angle: float) -> float:
        return map_range(
            angle,
            -90,
            90,
            self.MIN_PULSE_US,
            self.MAX_PULSE_US,
        )

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    # Compatibility aliases

    def angle(self, angle: Optional[float] = None):
        if angle is None:
            return self.get_angle()

        self.move_to(angle)

    def pulse_width_time(self, pulse_width_time: float) -> None:
        self.set_pulse_width_us(pulse_width_time)

    def close(self) -> None:
        if self._pwm is not None:
            self._pwm.close()
            self._pwm = None

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
