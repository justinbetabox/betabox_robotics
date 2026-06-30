from betabox_car.hardware import PWM, Motor, Pin, Servo
from betabox_car.robots import ROBOT


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
    ):
        self.left_motor = left_motor
        self.right_motor = right_motor
        self.steering = steering

        self.left_trim = float(left_trim)
        self.right_trim = float(right_trim)

    @classmethod
    def default(
        cls,
        *,
        robot_config=ROBOT,
        left_reversed: bool | None = None,
        right_reversed: bool | None = None,
        left_trim: float | None = None,
        right_trim: float | None = None,
        steering_min: float | None = None,
        steering_max: float | None = None,
    ):
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

    def speed(self, left: float, right: float):
        self.left_motor.set_speed(left * self.left_trim)
        self.right_motor.set_speed(right * self.right_trim)

    def forward(self, speed: float = 50):
        self.speed(abs(speed), abs(speed))

    def backward(self, speed: float = 50):
        self.speed(-abs(speed), -abs(speed))

    def left(self, angle: float = 30):
        self.steering.move_to(-abs(angle))

    def right(self, angle: float = 30):
        self.steering.move_to(abs(angle))

    def center(self):
        self.steering.center()

    def stop(self):
        self.left_motor.stop()
        self.right_motor.stop()

    def close(self):
        self.stop()
        self.left_motor.close()
        self.right_motor.close()
        self.steering.close()

    def deinit(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
