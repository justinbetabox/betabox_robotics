from __future__ import annotations

from typing import Self

from betabox_robotics.drive import DriveStatus

from .client import RobotRuntimeClient
from .control import RobotRuntimeControl


class RuntimeDrive:
    """Drive subsystem backed by the centralized robot runtime."""

    client: RobotRuntimeClient
    owner: str

    _control: RobotRuntimeControl | None
    _owns_control: bool
    _closed: bool

    def __init__(
        self,
        client: RobotRuntimeClient,
        *,
        owner: str = "Python application",
        control: RobotRuntimeControl | None = None,
    ) -> None:
        owner_value = owner.strip()

        if not owner_value:
            raise ValueError("owner cannot be empty")

        self.client = client
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
            raise RuntimeError("runtime drive subsystem is closed")

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

    def forward(
        self,
        speed: float,
    ) -> None:
        self._control_session().forward(
            speed,
        )

    def backward(
        self,
        speed: float,
    ) -> None:
        self._control_session().backward(
            speed,
        )

    def stop(
        self,
    ) -> None:
        self._control_session().stop()

    def left(
        self,
        angle: float = 30,
    ) -> None:
        self._control_session().left(
            angle,
        )

    def right(
        self,
        angle: float = 30,
    ) -> None:
        self._control_session().right(
            angle,
        )

    def center(
        self,
    ) -> None:
        self._control_session().center()

    def steering_angle(
        self,
        angle: float,
    ) -> None:
        self._control_session().steering_angle(
            angle,
        )

    def status(
        self,
    ) -> DriveStatus:
        self._require_open()

        status = self.client.drive_status()

        closed = status.get("closed")
        left_trim = status.get("left_trim")
        right_trim = status.get("right_trim")
        steering_offset = status.get("steering_offset")

        if not isinstance(
            closed,
            bool,
        ):
            raise TypeError("runtime drive closed state is invalid")

        if isinstance(
            left_trim,
            bool,
        ) or not isinstance(
            left_trim,
            int | float,
        ):
            raise TypeError("runtime drive left trim is invalid")

        if isinstance(
            right_trim,
            bool,
        ) or not isinstance(
            right_trim,
            int | float,
        ):
            raise TypeError("runtime drive right trim is invalid")

        if isinstance(
            steering_offset,
            bool,
        ) or not isinstance(
            steering_offset,
            int | float,
        ):
            raise TypeError("runtime drive steering offset is invalid")

        return DriveStatus(
            closed=closed,
            left_trim=float(left_trim),
            right_trim=float(right_trim),
            steering_offset=float(steering_offset),
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
