from dataclasses import dataclass

from betabox_robotics.audio import Audio
from betabox_robotics.drive import Drive
from betabox_robotics.hardware import AnalogChannel, DigitalPin, Pins, PWMChannel
from betabox_robotics.sensors import Sensors
from betabox_robotics.system import System
from betabox_robotics.vision import VisionClient

from .car import CarRobot


@dataclass(frozen=True)
class MotorConfig:
    pwm: PWMChannel
    direction: DigitalPin
    reversed: bool = False
    trim: float = 1.0


@dataclass(frozen=True)
class SteeringConfig:
    servo: PWMChannel
    min_angle: float = -30
    max_angle: float = 30


@dataclass(frozen=True)
class UltrasonicConfig:
    trigger: DigitalPin
    echo: DigitalPin


@dataclass(frozen=True)
class GrayscaleConfig:
    left: AnalogChannel
    middle: AnalogChannel
    right: AnalogChannel


@dataclass(frozen=True)
class BatteryConfig:
    channel: AnalogChannel
    scale: float = 3.0
    low_voltage: float = 6.6
    critical_voltage: float = 6.2


@dataclass(frozen=True)
class RobotConfig:
    left_motor: MotorConfig
    right_motor: MotorConfig
    steering: SteeringConfig
    ultrasonic: UltrasonicConfig
    grayscale: GrayscaleConfig
    battery: BatteryConfig


BETABOX_CAR = RobotConfig(
    left_motor=MotorConfig(
        pwm=Pins.P13,
        direction=Pins.D4,
        reversed=True,
        trim=1.0,
    ),
    right_motor=MotorConfig(
        pwm=Pins.P12,
        direction=Pins.D5,
        reversed=False,
        trim=1.0,
    ),
    steering=SteeringConfig(
        servo=Pins.P2,
        min_angle=-30,
        max_angle=30,
    ),
    ultrasonic=UltrasonicConfig(
        trigger=Pins.D2,
        echo=Pins.D3,
    ),
    grayscale=GrayscaleConfig(
        left=Pins.A0,
        middle=Pins.A1,
        right=Pins.A2,
    ),
    battery=BatteryConfig(
        channel=Pins.A4,
        scale=3.0,
        low_voltage=6.6,
        critical_voltage=6.2,
    ),
)


class BetaboxCar(CarRobot):
    """
    Concrete Betabox Car robot platform.
    """

    def __init__(self, config: RobotConfig = BETABOX_CAR):
        super().__init__()

        self.config = config

        self.drive = Drive.default(config)
        self.sensors = Sensors.default(config)
        self.vision = VisionClient()
        self.audio = Audio.default(config)
        self.system = System.default(config)

    def close(self) -> None:
        if self.closed:
            return

        self.stop_all()

        for subsystem in (
            self.audio,
            self.drive,
            self.sensors,
            self.system,
        ):
            close = getattr(subsystem, "close", None)

            if callable(close):
                close()

        self._closed = True
