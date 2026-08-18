from __future__ import annotations

import threading
from typing import Protocol, Self

from .errors import RobotRuntimeError

CONTROL_RENEW_INTERVAL = 0.75


class RuntimeControlClient(Protocol):
    """Client operations required by a managed control session."""

    def acquire_control(
        self,
        owner: str,
    ) -> str: ...

    def renew_control(
        self,
        token: str,
    ) -> None: ...

    def release_control(
        self,
        token: str,
    ) -> None: ...

    def drive_forward(
        self,
        token: str,
        speed: float = 20,
    ) -> None: ...

    def drive_backward(
        self,
        token: str,
        speed: float = 20,
    ) -> None: ...

    def drive_stop(
        self,
        token: str,
    ) -> None: ...

    def steering_left(
        self,
        token: str,
        angle: float = 30,
    ) -> None: ...

    def steering_right(
        self,
        token: str,
        angle: float = 30,
    ) -> None: ...

    def steering_center(
        self,
        token: str,
    ) -> None: ...

    def steering_angle(
        self,
        token: str,
        angle: float,
    ) -> None: ...

    def camera_pan(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None: ...

    def camera_tilt(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None: ...

    def camera_center(
        self,
        token: str,
        *,
        smooth: bool = True,
    ) -> None: ...


class RobotRuntimeControl:
    """Managed control lease for the Betabox robot runtime."""

    client: RuntimeControlClient
    owner: str

    _token: str | None
    _closed: bool
    _stop_event: threading.Event
    _renew_thread: threading.Thread | None

    def __init__(
        self,
        client: RuntimeControlClient,
        owner: str,
    ) -> None:

        owner_value = owner.strip()

        if not owner_value:
            raise ValueError("owner cannot be empty")

        self.client = client
        self.owner = owner_value

        self._token = None
        self._closed = False

        self._stop_event = threading.Event()
        self._renew_thread = None

    @property
    def closed(
        self,
    ) -> bool:
        return self._closed

    @property
    def token(
        self,
    ) -> str:
        token = self._token

        if token is None:
            raise RuntimeError("runtime control has not been acquired")

        return token

    @property
    def active(
        self,
    ) -> bool:
        return not self._closed and self._token is not None

    def start(
        self,
    ) -> None:
        if self._closed:
            raise RuntimeError("runtime control session is closed")

        if self._token is not None:
            return

        token = self.client.acquire_control(
            self.owner,
        )

        self._token = token
        self._stop_event.clear()

        thread = threading.Thread(
            target=self._renew_loop,
            name="betabox-runtime-control",
            daemon=True,
        )

        self._renew_thread = thread
        thread.start()

    def _renew_loop(
        self,
    ) -> None:
        while not self._stop_event.wait(CONTROL_RENEW_INTERVAL):
            token = self._token

            if token is None:
                return

            try:
                self.client.renew_control(token)
            except RobotRuntimeError:
                self._stop_event.set()
                return

    def forward(
        self,
        speed: float = 20,
    ) -> None:
        self.client.drive_forward(
            self.token,
            speed,
        )

    def backward(
        self,
        speed: float = 20,
    ) -> None:
        self.client.drive_backward(
            self.token,
            speed,
        )

    def stop(
        self,
    ) -> None:
        self.client.drive_stop(
            self.token,
        )

    def left(
        self,
        angle: float = 30,
    ) -> None:
        self.client.steering_left(
            self.token,
            angle,
        )

    def right(
        self,
        angle: float = 30,
    ) -> None:
        self.client.steering_right(
            self.token,
            angle,
        )

    def center(
        self,
    ) -> None:
        self.client.steering_center(
            self.token,
        )

    def steering_angle(
        self,
        angle: float,
    ) -> None:
        self.client.steering_angle(
            self.token,
            angle,
        )

    def camera_pan(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self.client.camera_pan(
            self.token,
            angle,
            smooth=smooth,
        )

    def camera_tilt(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        self.client.camera_tilt(
            self.token,
            angle,
            smooth=smooth,
        )

    def camera_center(
        self,
        *,
        smooth: bool = True,
    ) -> None:
        self.client.camera_center(
            self.token,
            smooth=smooth,
        )

    def close(
        self,
    ) -> None:
        if self._closed:
            return

        self._closed = True
        self._stop_event.set()

        thread = self._renew_thread
        self._renew_thread = None

        if thread is not None:
            thread.join(
                timeout=1.0,
            )

        token = self._token
        self._token = None

        if token is None:
            return

        try:
            self.client.release_control(token)
        except RobotRuntimeError:
            pass

    def __enter__(
        self,
    ) -> Self:
        self.start()

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
