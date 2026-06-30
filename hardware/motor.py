import logging
from enum import Enum
from time import sleep
from typing import Optional

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

    Mode 1: one PWM channel plus one direction pin.
    Mode 2: two PWM channels, one for each direction.
    """

    DEFAULT_FREQUENCY = 100
    DEFAULT_MAX_STEP = 5.0
    DEFAULT_STEP_DELAY = 0.01

    def __init__(
        self,
        pwm,
        direction,
        *,
        reversed: bool = False,
        mode: MotorMode = MotorMode.PWM_DIR,
        frequency: float = DEFAULT_FREQUENCY,
        max_step: float = DEFAULT_MAX_STEP,
        step_delay: float = DEFAULT_STEP_DELAY,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        if not isinstance(mode, MotorMode):
            raise MotorError("mode must be MotorMode.PWM_DIR or MotorMode.PWM_PWM")

        if max_step <= 0:
            raise MotorError("max_step must be greater than 0")

        if step_delay < 0:
            raise MotorError("step_delay cannot be negative")

        self.mode = mode
        self.reversed = bool(reversed)
        self.frequency = frequency
        self.max_step = float(max_step)
        self.step_delay = float(step_delay)

        self._speed = 0.0

        if self.mode == MotorMode.PWM_DIR:
            if not isinstance(pwm, PWM):
                raise MotorError("pwm must be a PWM instance")
            if not isinstance(direction, Pin):
                raise MotorError("direction must be a Pin instance")

            self.pwm = pwm
            self.direction = direction

            self.pwm.set_frequency(self.frequency)
            self.pwm.set_duty_cycle(0)

        elif self.mode == MotorMode.PWM_PWM:
            if not isinstance(pwm, PWM):
                raise MotorError("pwm must be a PWM instance")
            if not isinstance(direction, PWM):
                raise MotorError(
                    "direction must be a PWM instance when using PWM_PWM mode"
                )

            self.pwm_a = pwm
            self.pwm_b = direction

            self.pwm_a.set_frequency(self.frequency)
            self.pwm_a.set_duty_cycle(0)

            self.pwm_b.set_frequency(self.frequency)
            self.pwm_b.set_duty_cycle(0)

    def set_speed(self, speed: float, smooth: bool = True) -> None:
        if not isinstance(speed, (int, float)):
            raise MotorError(f"speed must be int or float, not {type(speed)}")

        target = self._clamp(float(speed), -100.0, 100.0)

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

            if self.step_delay:
                sleep(self.step_delay)

        self._set_speed_immediate(target)

    def get_speed(self) -> float:
        return self._speed

    def stop(self) -> None:
        self.set_speed(0)

    def forward(self, speed: float) -> None:
        self.set_speed(abs(speed))

    def backward(self, speed: float) -> None:
        self.set_speed(-abs(speed))

    def set_reversed(self, reversed: bool) -> None:
        self.reversed = bool(reversed)

    def _set_speed_immediate(self, speed: float) -> None:
        speed = self._clamp(speed, -100.0, 100.0)

        direction = speed > 0

        if self.reversed:
            direction = not direction

        duty = abs(speed)

        if self.mode == MotorMode.PWM_DIR:
            self.pwm.set_duty_cycle(duty)
            self.direction.write(direction)

        elif self.mode == MotorMode.PWM_PWM:
            if direction:
                self.pwm_a.set_duty_cycle(duty)
                self.pwm_b.set_duty_cycle(0)
            else:
                self.pwm_a.set_duty_cycle(0)
                self.pwm_b.set_duty_cycle(duty)

        self._speed = speed

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    # Compatibility alias
    def speed(self, speed: Optional[float] = None):
        if speed is None:
            return self.get_speed()

        self.set_speed(speed)

    def close(self) -> None:
        if self.mode == MotorMode.PWM_DIR:
            self.pwm.set_duty_cycle(0)
            self.pwm.close()
            self.direction.close()

        elif self.mode == MotorMode.PWM_PWM:
            self.pwm_a.set_duty_cycle(0)
            self.pwm_b.set_duty_cycle(0)
            self.pwm_a.close()
            self.pwm_b.close()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
