from __future__ import annotations

import math
import threading
from collections.abc import Callable
from time import sleep
from typing import TYPE_CHECKING, TypeVar

import lgpio
from gpiozero.exc import GPIOPinInUse

from betabox_robotics.camera import CameraMount
from betabox_robotics.drive import Drive
from betabox_robotics.exceptions import RobotBusyError
from betabox_robotics.hardware import (
    RobotOwnership,
    close_gpio_factory,
)
from betabox_robotics.sensors import Grayscale

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        CameraMountConfig,
        DriveConfig,
        GrayscaleConfig,
    )


ResultT = TypeVar("ResultT")


def _validate_number(
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


def _validate_trim(
    value: object,
    *,
    name: str,
) -> float:
    trim = _validate_number(
        value,
        name=name,
    )

    if not 0.0 <= trim <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")

    return trim


def _validate_samples(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("samples must be an integer")

    if value < 1:
        raise ValueError("samples must be at least 1")

    return value


class CalibrationHardware:
    """
    Run short-lived calibration hardware operations safely.

    Each operation is serialized, acquires exclusive robot ownership,
    constructs only the required hardware, and releases all resources
    before returning.

    Creating this object does not acquire robot hardware.
    """

    def __init__(
        self,
        *,
        drive_config: DriveConfig,
        camera_mount_config: CameraMountConfig,
        grayscale_config: GrayscaleConfig,
    ) -> None:
        self._drive_config = drive_config
        self._camera_mount_config = camera_mount_config
        self._grayscale_config = grayscale_config
        self._operation_lock = threading.Lock()

    def preview_steering(
        self,
        *,
        offset: float,
    ) -> None:
        offset_value = _validate_number(
            offset,
            name="steering offset",
        )

        steering = self._drive_config.steering

        if not (steering.min_angle <= offset_value <= steering.max_angle):
            raise ValueError(
                "steering offset must be between "
                f"{steering.min_angle} and "
                f"{steering.max_angle}"
            )

        self._run(
            self._preview_steering,
            owner=("Launchpad Steering Calibration"),
            offset=offset_value,
        )

    def preview_camera_mount(
        self,
        *,
        pan_offset: float,
        tilt_offset: float,
    ) -> None:
        pan_value = _validate_number(
            pan_offset,
            name="pan offset",
        )
        tilt_value = _validate_number(
            tilt_offset,
            name="tilt offset",
        )

        config = self._camera_mount_config

        if not (config.pan_min_angle <= pan_value <= config.pan_max_angle):
            raise ValueError(
                "pan offset must be between "
                f"{config.pan_min_angle} and "
                f"{config.pan_max_angle}"
            )

        if not (config.tilt_min_angle <= tilt_value <= config.tilt_max_angle):
            raise ValueError(
                "tilt offset must be between "
                f"{config.tilt_min_angle} and "
                f"{config.tilt_max_angle}"
            )

        self._run(
            self._preview_camera_mount,
            owner=("Launchpad Camera Calibration"),
            pan_offset=pan_value,
            tilt_offset=tilt_value,
        )

    def preview_motor_trim(
        self,
        *,
        left_trim: float,
        right_trim: float,
        steering_offset: float,
    ) -> None:
        left_value = _validate_trim(
            left_trim,
            name="left trim",
        )
        right_value = _validate_trim(
            right_trim,
            name="right trim",
        )
        steering_value = _validate_number(
            steering_offset,
            name="steering offset",
        )

        steering = self._drive_config.steering

        if not (steering.min_angle <= steering_value <= steering.max_angle):
            raise ValueError(
                "steering offset must be between "
                f"{steering.min_angle} and "
                f"{steering.max_angle}"
            )

        self._run(
            self._preview_motor_trim,
            owner=("Launchpad Motor Calibration"),
            left_trim=left_value,
            right_trim=right_value,
            steering_offset=steering_value,
        )

    def sample_grayscale(
        self,
        *,
        samples: int = 10,
    ) -> list[int]:
        sample_count = _validate_samples(samples)

        return self._run(
            self._sample_grayscale,
            owner=("Launchpad Grayscale Calibration"),
            samples=sample_count,
        )

    def _run(
        self,
        operation: Callable[..., ResultT],
        *,
        owner: str,
        **kwargs: object,
    ) -> ResultT:
        with self._operation_lock:
            ownership = RobotOwnership(
                owner=owner,
            )

            ownership.acquire()

            try:
                try:
                    return operation(**kwargs)
                except (
                    GPIOPinInUse,
                    lgpio.error,
                ) as exc:
                    raise RobotBusyError(
                        "The robot hardware could not "
                        "be acquired. Another application "
                        "may be using it."
                    ) from exc
            finally:
                try:
                    close_gpio_factory()
                finally:
                    ownership.release()

    def _preview_steering(
        self,
        *,
        offset: float,
    ) -> None:
        with Drive.default(
            self._drive_config,
            steering_offset=offset,
        ) as drive:
            drive.center()

    def _preview_camera_mount(
        self,
        *,
        pan_offset: float,
        tilt_offset: float,
    ) -> None:
        with CameraMount.default(
            self._camera_mount_config,
            pan_offset=pan_offset,
            tilt_offset=tilt_offset,
        ) as camera:
            camera.center()

    def _preview_motor_trim(
        self,
        *,
        left_trim: float,
        right_trim: float,
        steering_offset: float,
    ) -> None:
        with Drive.default(
            self._drive_config,
            left_trim=left_trim,
            right_trim=right_trim,
            steering_offset=steering_offset,
        ) as drive:
            drive.center()

            try:
                drive.forward(25)
                sleep(1.5)
            finally:
                drive.stop()

    def _sample_grayscale(
        self,
        *,
        samples: int,
    ) -> list[int]:
        totals = [
            0.0,
            0.0,
            0.0,
        ]

        with Grayscale.default(
            self._grayscale_config,
        ) as grayscale:
            for _ in range(samples):
                values = grayscale.read()

                totals[0] += values[0]
                totals[1] += values[1]
                totals[2] += values[2]

        return [round(total / samples) for total in totals]
