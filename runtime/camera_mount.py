from __future__ import annotations

import math
from typing import TYPE_CHECKING, Self

from betabox_robotics.camera import CameraMountStatus
from betabox_robotics.robots.config import CameraMountConfig

from .client import RobotRuntimeClient
from .control import RobotRuntimeControl

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        CameraMountConfig,
    )


class RuntimeCameraMount:
    """Camera mount backed by the centralized robot runtime."""

    client: RobotRuntimeClient
    config: CameraMountConfig
    owner: str

    _control: RobotRuntimeControl | None
    _owns_control: bool
    _closed: bool

    def __init__(
        self,
        client: RobotRuntimeClient,
        config: CameraMountConfig,
        *,
        owner: str = "Python application",
        control: RobotRuntimeControl | None = None,
    ) -> None:
        owner_value = owner.strip()

        if not owner_value:
            raise ValueError("owner cannot be empty")

        self.client = client
        self.config = config
        self.owner = owner_value

        self._control = control
        self._owns_control = control is None
        self._closed = False

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    def _require_open(
        self,
    ) -> None:
        if self._closed:
            raise RuntimeError("runtime camera mount is closed")

    @staticmethod
    def _number(
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

    def _control_session(
        self,
    ) -> RobotRuntimeControl:
        self._require_open()

        control = self._control

        if control is not None:
            if control.closed:
                raise RuntimeError("runtime control session is closed")

            if not control.active:
                control.start()

            return control

        control = self.client.control(
            self.owner,
        )
        control.start()

        self._control = control
        self._owns_control = True

        return control

    def look(
        self,
        *,
        pan: float | None = None,
        tilt: float | None = None,
        smooth: bool = True,
    ) -> None:
        self._require_open()

        pan_value = (
            None
            if pan is None
            else self._number(
                pan,
                name="pan",
            )
        )

        tilt_value = (
            None
            if tilt is None
            else self._number(
                tilt,
                name="tilt",
            )
        )

        control = self._control_session()

        if pan_value is not None:
            control.camera_pan(
                pan_value,
                smooth=smooth,
            )

        if tilt_value is not None:
            control.camera_tilt(
                tilt_value,
                smooth=smooth,
            )

    def pan(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        angle_value = self._number(
            angle,
            name="angle",
        )

        self._control_session().camera_pan(
            angle_value,
            smooth=smooth,
        )

    def tilt(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        angle_value = self._number(
            angle,
            name="angle",
        )

        self._control_session().camera_tilt(
            angle_value,
            smooth=smooth,
        )

    def center(
        self,
        *,
        smooth: bool = True,
    ) -> None:
        self._control_session().camera_center(
            smooth=smooth,
        )

    def status(
        self,
    ) -> CameraMountStatus:
        self._require_open()

        data = self.client.camera_mount_status()

        return CameraMountStatus(
            pan=self._optional_number(
                data.get("pan"),
                name="pan",
            ),
            tilt=self._optional_number(
                data.get("tilt"),
                name="tilt",
            ),
            pan_offset=self._required_number(
                data,
                "pan_offset",
            ),
            tilt_offset=self._required_number(
                data,
                "tilt_offset",
            ),
            pan_min=self._required_number(
                data,
                "pan_min",
            ),
            pan_max=self._required_number(
                data,
                "pan_max",
            ),
            tilt_min=self._required_number(
                data,
                "tilt_min",
            ),
            tilt_max=self._required_number(
                data,
                "tilt_max",
            ),
        )

    @classmethod
    def _optional_number(
        cls,
        value: object,
        *,
        name: str,
    ) -> float | None:
        if value is None:
            return None

        return cls._number(
            value,
            name=name,
        )

    @classmethod
    def _required_number(
        cls,
        data: dict[str, float | None],
        key: str,
    ) -> float:
        value = data.get(key)

        if value is None:
            raise RuntimeError(f"runtime camera mount {key} is missing")

        return cls._number(
            value,
            name=key,
        )

    def close(
        self,
    ) -> None:
        if self._closed:
            return

        self._closed = True

        control = self._control
        self._control = None

        if control is not None and self._owns_control:
            control.close()

    def deinit(
        self,
    ) -> None:
        self.close()

    def __enter__(
        self,
    ) -> Self:
        self._require_open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
