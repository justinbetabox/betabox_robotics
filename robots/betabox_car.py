from __future__ import annotations

import logging

import lgpio  # pyright: ignore[reportMissingTypeStubs]
from gpiozero.exc import GPIOPinInUse  # pyright: ignore[reportMissingTypeStubs]
from typing_extensions import override

from betabox_robotics.audio import Audio
from betabox_robotics.calibration import (
    RobotCalibration,
)
from betabox_robotics.camera import (
    CameraMount,
)
from betabox_robotics.drive import Drive
from betabox_robotics.exceptions import (
    RobotBusyError,
)
from betabox_robotics.hardware import (
    Pins,
    RobotOwnership,
    close_gpio_factory,
)
from betabox_robotics.sensors import Sensors
from betabox_robotics.system import System
from betabox_robotics.vision import VisionClient

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

logger = logging.getLogger(__name__)

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

    config: RobotConfig
    calibration: RobotCalibration

    _drive: Drive
    _sensors: Sensors
    _camera_mount: CameraMount
    _vision: VisionClient
    _audio: Audio
    _system: System

    _ownership: RobotOwnership
    _started: bool
    _closed: bool

    def __init__(
        self,
        config: RobotConfig = BETABOX_CAR,
        *,
        owner: str = "Python application",
        calibration: RobotCalibration | None = None,
    ) -> None:
        super().__init__()

        self.config = config
        self.calibration = (
            RobotCalibration.default() if calibration is None else calibration
        )

        self._ownership = RobotOwnership(owner=owner)

        # Acquisition intentionally remains outside the cleanup block.
        # A failed acquisition must not close GPIO resources owned by
        # another process.
        self._ownership.acquire()

        try:
            self._drive = Drive.default(
                config.drive,
                left_trim=self.calibration.motors.left_trim,
                right_trim=self.calibration.motors.right_trim,
                steering_offset=self.calibration.steering.offset,
            )

            self._sensors = Sensors.default(config.sensors)

            grayscale_calibration = self.calibration.grayscale

            if grayscale_calibration.calibrated:
                floor = grayscale_calibration.floor
                line = grayscale_calibration.line

                if floor is None or line is None:
                    raise ValueError(
                        "calibrated grayscale data must contain floor and line values"
                    )

                self._sensors.grayscale.set_calibration(
                    floor,
                    line,
                )

            self._camera_mount = CameraMount.default(
                config.camera_mount,
                pan_offset=self.calibration.camera_mount.pan_offset,
                tilt_offset=self.calibration.camera_mount.tilt_offset,
            )

            self._vision = VisionClient.default(config.vision)

            self._audio = Audio.default(config.audio)

            self._system = System.default(config.system)

            self.start()

        except (
            GPIOPinInUse,
            lgpio.error,
        ) as exc:
            self._close_constructed_subsystems()
            self._ownership.release()

            raise RobotBusyError(
                "The robot hardware could not be acquired. Another process may be using it."
            ) from exc

        except Exception:
            self._close_constructed_subsystems()
            self._ownership.release()
            raise

    @property
    @override
    def drive(self) -> Drive:
        return self._drive

    @property
    @override
    def sensors(self) -> Sensors:
        return self._sensors

    @property
    @override
    def camera_mount(self) -> CameraMount:
        return self._camera_mount

    @property
    @override
    def vision(self) -> VisionClient:
        return self._vision

    @property
    @override
    def audio(self) -> Audio:
        return self._audio

    @property
    @override
    def system(self) -> System:
        return self._system

    @override
    def close(self) -> None:
        if self.closed:
            return

        try:
            self.stop_all()
        finally:
            try:
                self._close_constructed_subsystems()
            finally:
                try:
                    close_gpio_factory()
                finally:
                    self._ownership.release()
                    self._started = False
                    self._closed = True

    def _close_constructed_subsystems(
        self,
    ) -> None:
        if hasattr(self, "_audio"):
            try:
                self._audio.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close audio subsystem.")

        if hasattr(self, "_camera_mount"):
            try:
                self._camera_mount.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close camera mount subsystem.")

        if hasattr(self, "_drive"):
            try:
                self._drive.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close drive subsystem.")

        if hasattr(self, "_sensors"):
            try:
                self._sensors.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close sensors subsystem.")

        if hasattr(self, "_system"):
            try:
                self._system.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close system subsystem.")
