from dataclasses import asdict, dataclass
from typing import Any, Self

from betabox_robotics.hardware import PWM, Motor, Pin, Servo
from .exceptions import DriveError

@dataclass(frozen=True)
class DriveStatus:
    closed: bool
    left_trim: float
    right_trim: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class Drive:
    """
    Betabox car drive subsystem.

    Drive owns car movement behavior, but does not need to know how
    each Motor or Servo is wired unless using the default hardware setup.
    """

    def __init__(
        self,
        left_motor: Motor,
        right_motor: Motor,
        steering: Servo,
        *,
        left_trim: float = 1.0,
        right_trim: float = 1.0,
    ) -> None:
        if left_trim < 0:
            raise DriveError("left_trim cannot be negative")

        if right_trim < 0:
            raise DriveError("right_trim cannot be negative")

        self.left_motor = left_motor
        self.right_motor = right_motor
        self.steering = steering

        self.left_trim = float(left_trim)
        self.right_trim = float(right_trim)
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed


    def _require_open(self) -> None:
        if self._closed:
            raise DriveError("drive subsystem is closed")

    @classmethod
    def default(
        cls,
        robot_config,
        *,
        left_reversed: bool | None = None,
        right_reversed: bool | None = None,
        left_trim: float | None = None,
        right_trim: float | None = None,
        steering_min: float | None = None,
        steering_max: float | None = None,
    ) -> "Drive":
        left_cfg = robot_config.left_motor
        right_cfg = robot_config.right_motor
        steering_cfg = robot_config.steering

        left_motor = Motor(
            PWM(left_cfg.pwm),
            Pin(left_cfg.direction, mode=Pin.OUT),
            reversed=left_cfg.reversed if left_reversed is None else left_reversed,
        )

        right_motor = Motor(
            PWM(right_cfg.pwm),
            Pin(right_cfg.direction, mode=Pin.OUT),
            reversed=right_cfg.reversed if right_reversed is None else right_reversed,
        )

        steering = Servo(
            steering_cfg.servo,
            min_angle=steering_cfg.min_angle if steering_min is None else steering_min,
            max_angle=steering_cfg.max_angle if steering_max is None else steering_max,
        )

        return cls(
            left_motor=left_motor,
            right_motor=right_motor,
            steering=steering,
            left_trim=left_cfg.trim if left_trim is None else left_trim,
            right_trim=right_cfg.trim if right_trim is None else right_trim,
        )

    def speed(self, left: float, right: float) -> None:
        self._require_open()

        left_speed = self._validate_speed(left)
        right_speed = self._validate_speed(right)

        self.left_motor.set_speed(
            self._clamp_speed(left_speed * self.left_trim)
        )
        self.right_motor.set_speed(
            self._clamp_speed(right_speed * self.right_trim)
        )

    def forward(self, speed: float = 50) -> None:
        self._require_open()
        speed = self._validate_speed(abs(speed))
        self.speed(speed, speed)


    def backward(self, speed: float = 50) -> None:
        self._require_open()
        speed = self._validate_speed(abs(speed))
        self.speed(-speed, -speed)


    def left(self, angle: float = 30) -> None:
        self._require_open()
        self.steering.move_to(-abs(float(angle)))


    def right(self, angle: float = 30) -> None:
        self._require_open()
        self.steering.move_to(abs(float(angle)))


    def center(self) -> None:
        self._require_open()
        self.steering.center()


    def stop(self) -> None:
        self._require_open()
        self.left_motor.stop()
        self.right_motor.stop()

    def status(self) -> DriveStatus:
        return DriveStatus(
            closed=self.closed,
            left_trim=self.left_trim,
            right_trim=self.right_trim,
        )

    @staticmethod
    def _validate_speed(value: float) -> float:
        speed = float(value)

        if not -100.0 <= speed <= 100.0:
            raise DriveError("speed must be between -100 and 100")

        return speed

    @staticmethod
    def _clamp_speed(value: float) -> float:
        return max(-100.0, min(100.0, value))

    def close(self) -> None:
        if self._closed:
            return

        try:
            self.left_motor.stop()
            self.right_motor.stop()
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
