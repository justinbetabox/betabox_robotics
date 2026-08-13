from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from betabox_robotics.hardware import (
    PWM,
    HardwareError,
    Motor,
    Pin,
    PinMode,
    Servo,
)

from .exceptions import DriveError

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        DriveConfig,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DriveStatus:
    closed: bool
    left_trim: float
    right_trim: float
    steering_offset: float

    def to_dict(
        self,
    ) -> dict[str, bool | float]:
        return {
            "closed": self.closed,
            "left_trim": self.left_trim,
            "right_trim": self.right_trim,
            "steering_offset": self.steering_offset,
        }


class Drive:
    """
    Betabox car drive subsystem.

    Drive owns car movement behavior, but does not need to know how
    each Motor or Servo is wired unless using the default hardware setup.
    """

    left_motor: Motor
    right_motor: Motor
    steering: Servo

    left_trim: float
    right_trim: float

    _closed: bool

    def __init__(
        self,
        left_motor: Motor,
        right_motor: Motor,
        steering: Servo,
        *,
        left_trim: float = 1.0,
        right_trim: float = 1.0,
    ) -> None:
        left_trim_value = self._require_finite_number(
            left_trim,
            name="left_trim",
        )

        right_trim_value = self._require_finite_number(
            right_trim,
            name="right_trim",
        )

        if left_trim_value < 0:
            raise DriveError("left_trim cannot be negative")

        if right_trim_value < 0:
            raise DriveError("right_trim cannot be negative")

        self.left_motor = left_motor
        self.right_motor = right_motor
        self.steering = steering

        self.left_trim = left_trim_value
        self.right_trim = right_trim_value
        self._closed = False

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
            raise DriveError("drive subsystem is closed")

    @classmethod
    def default(
        cls,
        config: DriveConfig,
        *,
        left_reversed: bool | None = None,
        right_reversed: bool | None = None,
        left_trim: float | None = None,
        right_trim: float | None = None,
        steering_min: float | None = None,
        steering_max: float | None = None,
        steering_offset: float = 0.0,
    ) -> Self:
        left_motor: Motor | None = None
        right_motor: Motor | None = None
        steering: Servo | None = None

        try:
            left_cfg = config.left_motor
            right_cfg = config.right_motor
            steering_cfg = config.steering

            left_motor = Motor(
                PWM(left_cfg.pwm),
                Pin(
                    left_cfg.direction,
                    mode=PinMode.OUT,
                ),
                reversed=(
                    left_cfg.reversed if left_reversed is None else left_reversed
                ),
            )

            right_motor = Motor(
                PWM(right_cfg.pwm),
                Pin(
                    right_cfg.direction,
                    mode=PinMode.OUT,
                ),
                reversed=(
                    right_cfg.reversed if right_reversed is None else right_reversed
                ),
            )

            steering = Servo(
                steering_cfg.servo,
                min_angle=(
                    steering_cfg.min_angle if steering_min is None else steering_min
                ),
                max_angle=(
                    steering_cfg.max_angle if steering_max is None else steering_max
                ),
                offset=steering_offset,
            )

            return cls(
                left_motor=left_motor,
                right_motor=right_motor,
                steering=steering,
                left_trim=(left_cfg.trim if left_trim is None else left_trim),
                right_trim=(right_cfg.trim if right_trim is None else right_trim),
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            for component in (
                steering,
                right_motor,
                left_motor,
            ):
                if component is None:
                    continue

                try:
                    component.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            raise

    def speed(
        self,
        left: float,
        right: float,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        left_speed = self._validate_speed(left)
        right_speed = self._validate_speed(right)

        left_target = self._clamp_speed(left_speed * self.left_trim)

        right_target = self._clamp_speed(right_speed * self.right_trim)

        try:
            self.left_motor.set_speed(
                left_target,
                smooth=smooth,
            )

            self.right_motor.set_speed(
                right_target,
                smooth=smooth,
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
        ):
            self._emergency_stop_motors()
            raise

    def forward(
        self,
        speed: float = 50,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        value = self._require_finite_number(
            speed,
            name="speed",
        )

        magnitude = self._validate_speed(abs(value))

        self.speed(
            magnitude,
            magnitude,
            smooth=smooth,
        )

    def backward(
        self,
        speed: float = 50,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        value = self._require_finite_number(
            speed,
            name="speed",
        )

        magnitude = self._validate_speed(abs(value))

        self.speed(
            -magnitude,
            -magnitude,
            smooth=smooth,
        )

    def left(
        self,
        angle: float = 30,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        value = self._require_finite_number(
            angle,
            name="angle",
        )

        self.steering.move_to(
            -abs(value),
            smooth=smooth,
        )

    def right(
        self,
        angle: float = 30,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        value = self._require_finite_number(
            angle,
            name="angle",
        )

        self.steering.move_to(
            abs(value),
            smooth=smooth,
        )

    def center(
        self,
        *,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        self.steering.move_to(
            0,
            smooth=smooth,
        )

    def stop(self) -> None:
        """Ramp both motors to a controlled stop."""

        self._require_open()

        first_error: HardwareError | OSError | RuntimeError | None = None

        for motor in (
            self.left_motor,
            self.right_motor,
        ):
            try:
                motor.stop()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

        if first_error is not None:
            self._emergency_stop_motors()
            raise first_error

    def emergency_stop(self) -> None:
        """Immediately remove drive output from both motors."""

        self._require_open()

        first_error: HardwareError | OSError | RuntimeError | None = None

        for motor in (
            self.left_motor,
            self.right_motor,
        ):
            try:
                motor.emergency_stop()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ) as exc:
                if first_error is None:
                    first_error = exc

        if first_error is not None:
            raise first_error

    def _emergency_stop_motors(
        self,
    ) -> None:
        for motor in (
            self.left_motor,
            self.right_motor,
        ):
            try:
                if not motor.closed:
                    motor.emergency_stop()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass

    def status(self) -> DriveStatus:
        return DriveStatus(
            closed=self.closed,
            left_trim=self.left_trim,
            right_trim=self.right_trim,
            steering_offset=self.steering.offset,
        )

    @classmethod
    def _validate_speed(
        cls,
        value: float,
    ) -> float:
        speed = cls._require_finite_number(
            value,
            name="speed",
        )

        if not -100.0 <= speed <= 100.0:
            raise DriveError("speed must be between -100 and 100")

        return speed

    @staticmethod
    def _clamp_speed(
        value: float,
    ) -> float:
        return max(
            -100.0,
            min(
                100.0,
                value,
            ),
        )

    def deinit(self) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return

        try:
            self._emergency_stop_motors()
        finally:
            try:
                self.left_motor.close()
            finally:
                try:
                    self.right_motor.close()
                finally:
                    try:
                        self.steering.close()
                    finally:
                        self._closed = True

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
