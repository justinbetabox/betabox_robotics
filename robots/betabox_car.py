from betabox_robotics.audio import Audio
from betabox_robotics.drive import Drive
from betabox_robotics.hardware import Pins
from betabox_robotics.sensors import Sensors
from betabox_robotics.system import System
from betabox_robotics.vision import VisionClient

from .car import CarRobot
from .config import (
    AudioConfig,
    BatteryConfig,
    DriveConfig,
    GrayscaleConfig,
    MotorConfig,
    RobotConfig,
    SensorsConfig,
    SteeringConfig,
    SystemConfig,
    UltrasonicConfig,
    VisionConfig,
)


BETABOX_CAR = RobotConfig(
    drive=DriveConfig(
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
    ),
    sensors=SensorsConfig(
        ultrasonic=UltrasonicConfig(
            trigger=Pins.D2,
            echo=Pins.D3,
            timeout=0.02,
        ),
        grayscale=GrayscaleConfig(
            left=Pins.A0,
            middle=Pins.A1,
            right=Pins.A2,
            reference=(1000, 1000, 1000),
        ),
        battery=BatteryConfig(
            channel=Pins.A4,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        ),
    ),
    vision=VisionConfig(),
    audio=AudioConfig(),
    system=SystemConfig(),
)


class BetaboxCar(CarRobot):
    """
    Concrete Betabox Car robot platform.
    """

    def __init__(self, config: RobotConfig = BETABOX_CAR):
        super().__init__()

        self.config = config

        # Temporary compatibility during the nested-config migration.
        # These factories will be updated in the next step.
        self.drive = Drive.default(config.drive)
        self.sensors = Sensors.default(config.sensors)
        self.vision = VisionClient.default(config.vision)
        self.audio = Audio.default(config.audio)
        self.system = System.default(config.system)

        self.start()

    def close(self) -> None:
        if self.closed:
            return

        try:
            self.stop_all()
        finally:
            for subsystem in (
                self.audio,
                self.drive,
                self.sensors,
                self.system,
            ):
                close = getattr(subsystem, "close", None)

                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass

            self._started = False
            self._closed = True
