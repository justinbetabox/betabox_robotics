from __future__ import annotations

import logging
from contextlib import ExitStack

from typing_extensions import override

from betabox_robotics.audio import Audio
from betabox_robotics.calibration import RobotCalibration
from betabox_robotics.runtime.camera_mount import (
    RuntimeCameraMount,
)
from betabox_robotics.runtime.client import (
    RobotRuntimeClient,
)
from betabox_robotics.runtime.control import (
    RobotRuntimeControl,
)
from betabox_robotics.runtime.drive import (
    RuntimeDrive,
)
from betabox_robotics.runtime.errors import (
    RobotRuntimeError,
)
from betabox_robotics.runtime.sensors import (
    RuntimeSensors,
)
from betabox_robotics.system import System
from betabox_robotics.vision import VisionClient

from .car import CarRobot
from .config import RobotConfig
from .defaults import BETABOX_CAR

logger = logging.getLogger(__name__)


class BetaboxCar(CarRobot):
    """
    Concrete Betabox Car robot platform.

    Hardware-backed drive, sensors, and camera mount operations are provided
    by the centralized Betabox Robot Runtime.
    """

    config: RobotConfig
    calibration: RobotCalibration

    _runtime_client: RobotRuntimeClient
    _runtime_control: RobotRuntimeControl

    _drive: RuntimeDrive
    _sensors: RuntimeSensors
    _camera_mount: RuntimeCameraMount

    _vision: VisionClient
    _audio: Audio
    _system: System

    def __init__(
        self,
        config: RobotConfig = BETABOX_CAR,
        *,
        owner: str = "Python application",
        calibration: RobotCalibration | None = None,
    ) -> None:
        super().__init__()

        owner_value = owner.strip()

        if not owner_value:
            raise ValueError("owner cannot be empty")

        self.config = config
        self.calibration = (
            RobotCalibration.default() if calibration is None else calibration
        )

        self._runtime_client = RobotRuntimeClient()

        runtime_status = self._runtime_client.status()

        if not runtime_status.ready:
            raise RobotRuntimeError("Betabox Robot Runtime is not ready")

        if not runtime_status.hardware_initialized:
            raise RobotRuntimeError("Betabox Robot Runtime hardware is not initialized")

        with ExitStack() as stack:
            self._runtime_control = self._runtime_client.control(
                owner_value,
            )
            _ = stack.callback(
                self._runtime_control.close,
            )

            self._drive = RuntimeDrive(
                self._runtime_client,
                owner=owner_value,
                control=self._runtime_control,
            )
            _ = stack.callback(
                self._drive.close,
            )

            self._sensors = RuntimeSensors(
                self._runtime_client,
                battery_config=config.sensors.battery,
                grayscale_config=config.sensors.grayscale,
                calibration=self.calibration,
            )
            _ = stack.callback(
                self._sensors.close,
            )

            self._camera_mount = RuntimeCameraMount(
                self._runtime_client,
                config.camera_mount,
                owner=owner_value,
                control=self._runtime_control,
            )
            _ = stack.callback(
                self._camera_mount.close,
            )

            self._vision = VisionClient.default(
                config.vision,
            )

            self._audio = Audio.default(
                config.audio,
            )
            _ = stack.callback(
                self._audio.close,
            )

            self._system = System.default(
                config.system,
            )
            _ = stack.callback(
                self._system.close,
            )

            self.start()

            _ = stack.pop_all()

    @property
    @override
    def drive(
        self,
    ) -> RuntimeDrive:
        return self._drive

    @property
    @override
    def sensors(
        self,
    ) -> RuntimeSensors:
        return self._sensors

    @property
    @override
    def camera_mount(
        self,
    ) -> RuntimeCameraMount:
        return self._camera_mount

    @property
    @override
    def vision(
        self,
    ) -> VisionClient:
        return self._vision

    @property
    @override
    def audio(
        self,
    ) -> Audio:
        return self._audio

    @property
    @override
    def system(
        self,
    ) -> System:
        return self._system

    @override
    def close(
        self,
    ) -> None:
        if self.closed:
            return

        try:
            self.stop_all()

        finally:
            try:
                self._close_constructed_subsystems()

            finally:
                self._runtime_control.close()

                super().close()

    def _close_constructed_subsystems(
        self,
    ) -> None:
        if hasattr(
            self,
            "_audio",
        ):
            try:
                self._audio.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close audio subsystem.")

        if hasattr(
            self,
            "_camera_mount",
        ):
            try:
                self._camera_mount.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close camera mount subsystem.")

        if hasattr(
            self,
            "_drive",
        ):
            try:
                self._drive.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close drive subsystem.")

        if hasattr(
            self,
            "_sensors",
        ):
            try:
                self._sensors.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close sensors subsystem.")

        if hasattr(
            self,
            "_system",
        ):
            try:
                self._system.close()
            except (
                OSError,
                RuntimeError,
            ):
                logger.exception("Failed to close system subsystem.")
