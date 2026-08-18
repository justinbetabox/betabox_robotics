from __future__ import annotations

import math
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from betabox_robotics.exceptions import RobotBusyError
from betabox_robotics.runtime.client import RobotRuntimeClient
from betabox_robotics.runtime.errors import RobotRuntimeError

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        CameraMountConfig,
        DriveConfig,
        GrayscaleConfig,
    )


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
    Run calibration hardware operations through the centralized robot runtime.

    Operations are serialized locally. Actuator previews acquire a runtime
    control lease, while read-only sensor sampling does not require control.

    Creating this object does not acquire robot control or hardware.
    """

    _drive_config: DriveConfig
    _camera_mount_config: CameraMountConfig
    _grayscale_config: GrayscaleConfig
    _operation_lock: threading.Lock

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
                + f"{steering.min_angle} and "
                + f"{steering.max_angle}"
            )

        self._run_preview(
            self._preview_steering,
            owner="Launchpad Steering Calibration",
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
                + f"{config.pan_min_angle} and "
                + f"{config.pan_max_angle}"
            )

        if not (config.tilt_min_angle <= tilt_value <= config.tilt_max_angle):
            raise ValueError(
                "tilt offset must be between "
                + f"{config.tilt_min_angle} and "
                + f"{config.tilt_max_angle}"
            )

        self._run_preview(
            self._preview_camera_mount,
            owner="Launchpad Camera Calibration",
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
                + f"{steering.min_angle} and "
                + f"{steering.max_angle}"
            )

        self._run_preview(
            self._preview_motor_trim,
            owner="Launchpad Motor Calibration",
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

        with self._operation_lock:
            client = RobotRuntimeClient()

            totals = [
                0.0,
                0.0,
                0.0,
            ]

            for _ in range(sample_count):
                values = client.grayscale_values()

                totals[0] += values[0]
                totals[1] += values[1]
                totals[2] += values[2]

        return [round(total / sample_count) for total in totals]

    def _run_preview(
        self,
        operation: Callable[..., None],
        *,
        owner: str,
        **kwargs: object,
    ) -> None:
        with self._operation_lock:
            client = RobotRuntimeClient()

            try:
                with client.control(owner) as control:
                    operation(
                        client=client,
                        token=control.token,
                        **kwargs,
                    )

            except RobotRuntimeError as exc:
                if str(exc).startswith("robot control is already owned by "):
                    raise RobotBusyError(
                        "The robot hardware could not be acquired. "
                        + "Another application may be using it."
                    ) from exc

                raise

    @staticmethod
    def _preview_steering(
        *,
        client: RobotRuntimeClient,
        token: str,
        offset: float,
    ) -> None:
        client.preview_steering_calibration(
            token,
            offset,
        )

    @staticmethod
    def _preview_camera_mount(
        *,
        client: RobotRuntimeClient,
        token: str,
        pan_offset: float,
        tilt_offset: float,
    ) -> None:
        client.preview_camera_calibration(
            token,
            pan_offset=pan_offset,
            tilt_offset=tilt_offset,
        )

    @staticmethod
    def _preview_motor_trim(
        *,
        client: RobotRuntimeClient,
        token: str,
        left_trim: float,
        right_trim: float,
        steering_offset: float,
    ) -> None:
        client.preview_motor_calibration(
            token,
            left_trim=left_trim,
            right_trim=right_trim,
            steering_offset=steering_offset,
        )
