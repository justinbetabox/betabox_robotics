from gpiozero.exc import GPIOPinInUse
import lgpio

from betabox_robotics.exceptions import (
    RobotBusyError,
)

from betabox_robotics.audio import Audio
from betabox_robotics.drive import Drive
from betabox_robotics.sensors import Sensors
from betabox_robotics.system import System
from betabox_robotics.vision import VisionClient
from betabox_robotics.camera import (
    CameraMount,
)
from betabox_robotics.hardware import (
    Pins,
    RobotOwnership,
    close_gpio_factory,
)

from .car import CarRobot
from .config import (
    AudioConfig,
    BatteryConfig,
    CameraMountConfig,
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
    camera_mount=CameraMountConfig(
        pan_servo=Pins.P0,
        tilt_servo=Pins.P1,
        pan_min_angle=-45.0,
        pan_max_angle=45.0,
        tilt_min_angle=-30.0,
        tilt_max_angle=45.0,
        pan_center=0.0,
        tilt_center=0.0,
        pan_reversed=True,
        tilt_reversed=True,
    ),
    vision=VisionConfig(),
    audio=AudioConfig(),
    system=SystemConfig(),
)


class BetaboxCar(CarRobot):
    """
    Concrete Betabox Car robot platform.
    """

    def __init__(
        self,
        config: RobotConfig = BETABOX_CAR,
        *,
        owner: str = "Python application",
    ) -> None:
        super().__init__()

        self.config = config

        self.drive = None
        self.sensors = None
        self.camera_mount = None
        self.vision = None
        self.audio = None
        self.system = None

        self._ownership = RobotOwnership(
            owner=owner
        )

        self._ownership.acquire()

        try:
            self.drive = Drive.default(
                config.drive
            )

            self.sensors = Sensors.default(
                config.sensors
            )

            self.camera_mount = CameraMount.default(
                config.camera_mount
            )

            self.vision = VisionClient.default(
                config.vision
            )

            self.audio = Audio.default(
                config.audio
            )

            self.system = System.default(
                config.system
            )

            self.start()

        except (
            GPIOPinInUse,
            lgpio.error,
        ) as exc:
            self._close_constructed_subsystems()
            self._ownership.release()

            raise RobotBusyError(
                "The robot hardware could not be acquired. "
                "Another process may be using it."
            ) from None

        except Exception:
            self._close_constructed_subsystems()
            self._ownership.release()
            raise

    def close(self) -> None:
        if self.closed:
            return

        try:
            self.stop_all()
        finally:
            try:
                self._close_constructed_subsystems()
                close_gpio_factory()
            finally:
                self._ownership.release()
                self._started = False
                self._closed = True


    def _close_constructed_subsystems(
        self,
    ) -> None:
        for subsystem in (
            self.audio,
            self.camera_mount,
            self.drive,
            self.sensors,
            self.system,
        ):
            if subsystem is None:
                continue

            close = getattr(
                subsystem,
                "close",
                None,
            )

            if callable(close):
                try:
                    close()
                except Exception:
                    pass
