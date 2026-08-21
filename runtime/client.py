from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import cast

from .control import RobotRuntimeControl
from .errors import (
    RobotRuntimeError,
    RobotRuntimeProtocolError,
    RobotRuntimeUnavailableError,
)
from .protocol import (
    PROTOCOL_VERSION,
    RUNTIME_SOCKET_PATH,
    RuntimeCommand,
    RuntimeRequest,
    RuntimeResponse,
    RuntimeStatus,
    decode_response,
    encode_request,
)

RESPONSE_LIMIT = 64 * 1024
DEFAULT_TIMEOUT = 2.0

CONNECT_RETRY_INTERVAL = 0.05


def _integer_result(
    data: dict[object, object],
    key: str,
) -> int:
    value = data.get(key)

    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise RobotRuntimeProtocolError(f"runtime {key} must be an integer")

    return value


def _number_result(
    data: dict[object, object],
    key: str,
) -> float:
    value = data.get(key)

    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise RobotRuntimeProtocolError(f"runtime {key} must be a number")

    return float(value)


class RobotRuntimeClient:
    """Client for the local Betabox robot runtime."""

    socket_path: Path
    timeout: float

    def __init__(
        self,
        *,
        socket_path: Path = RUNTIME_SOCKET_PATH,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:

        timeout_value = float(timeout)

        if timeout_value <= 0:
            raise ValueError("timeout must be greater than zero")

        self.socket_path = socket_path
        self.timeout = timeout_value

    def _connect(
        self,
        client: socket.socket,
    ) -> None:
        deadline = time.monotonic() + self.timeout
        last_error: OSError | None = None

        while True:
            try:
                client.connect(
                    str(self.socket_path),
                )
                return

            except (
                FileNotFoundError,
                ConnectionRefusedError,
            ) as exc:
                last_error = exc

            remaining = deadline - time.monotonic()

            if remaining <= 0:
                break

            time.sleep(
                min(
                    CONNECT_RETRY_INTERVAL,
                    remaining,
                )
            )

        raise RobotRuntimeUnavailableError(
            f"Betabox Robot Runtime is unavailable: {last_error}"
        ) from last_error

    def ping(
        self,
    ) -> bool:
        response = self._request("ping")

        if response.result != "pong":
            raise RobotRuntimeProtocolError("runtime returned an invalid ping response")

        return True

    def acquire_control(
        self,
        owner: str,
    ) -> str:
        """Acquire exclusive robot control."""

        owner_value = owner.strip()

        if not owner_value:
            raise ValueError("owner cannot be empty")

        response = self._request(
            "acquire_control",
            params={
                "owner": owner_value,
            },
        )

        result = response.result

        if not isinstance(
            result,
            dict,
        ):
            raise RobotRuntimeProtocolError(
                "runtime returned an invalid control response"
            )

        data = cast(
            dict[object, object],
            result,
        )

        token = data.get("token")

        if not isinstance(
            token,
            str,
        ):
            raise RobotRuntimeProtocolError("runtime control token must be a string")

        if not token:
            raise RobotRuntimeProtocolError("runtime control token cannot be empty")

        return token

    def release_control(
        self,
        token: str,
    ) -> None:
        """Release exclusive robot control."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "release_control",
            params={
                "token": token,
            },
        )

    def renew_control(
        self,
        token: str,
    ) -> None:
        """Renew the current robot control lease."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "renew_control",
            params={
                "token": token,
            },
        )

    def status(
        self,
    ) -> RuntimeStatus:
        response = self._request("status")

        result = response.result

        if not isinstance(result, dict):
            raise RobotRuntimeProtocolError(
                "runtime returned an invalid status response"
            )

        data = cast(
            dict[object, object],
            result,
        )

        ready = data.get("ready")
        ownership_acquired = data.get("ownership_acquired")
        hardware_initialized = data.get("hardware_initialized")
        control_owner = data.get("control_owner")
        pid = data.get("pid")

        if not isinstance(ready, bool):
            raise RobotRuntimeProtocolError("runtime status ready must be a boolean")

        if not isinstance(ownership_acquired, bool):
            raise RobotRuntimeProtocolError(
                "runtime status ownership_acquired must be a boolean"
            )

        if not isinstance(hardware_initialized, bool):
            raise RobotRuntimeProtocolError(
                "runtime status hardware_initialized must be a boolean"
            )

        if control_owner is not None and not isinstance(
            control_owner,
            str,
        ):
            raise RobotRuntimeProtocolError(
                "runtime status control_owner must be a string or None"
            )

        if isinstance(pid, bool) or not isinstance(
            pid,
            int,
        ):
            raise RobotRuntimeProtocolError("runtime status pid must be an integer")

        return RuntimeStatus(
            ready=ready,
            ownership_acquired=ownership_acquired,
            hardware_initialized=hardware_initialized,
            control_owner=control_owner,
            pid=pid,
        )

    def drive_status(
        self,
    ) -> dict[str, bool | float]:
        """Return the current drive subsystem status."""

        response = self._request("drive_status")

        result = response.result

        if not isinstance(
            result,
            dict,
        ):
            raise RobotRuntimeProtocolError(
                "runtime returned an invalid drive status response"
            )

        data = cast(
            dict[object, object],
            result,
        )

        closed = data.get("closed")
        left_trim = data.get("left_trim")
        right_trim = data.get("right_trim")
        steering_offset = data.get("steering_offset")

        if not isinstance(
            closed,
            bool,
        ):
            raise RobotRuntimeProtocolError(
                "runtime drive status closed must be a boolean"
            )

        for name, value in (
            ("left_trim", left_trim),
            ("right_trim", right_trim),
            ("steering_offset", steering_offset),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                int | float,
            ):
                raise RobotRuntimeProtocolError(
                    f"runtime drive status {name} must be a number"
                )

        return {
            "closed": closed,
            "left_trim": _number_result(data, "left_trim"),
            "right_trim": _number_result(data, "right_trim"),
            "steering_offset": _number_result(data, "steering_offset"),
        }

    def camera_mount_status(
        self,
    ) -> dict[str, float | None]:
        response = self._request("camera_mount_status")

        result = response.result

        if not isinstance(
            result,
            dict,
        ):
            raise RobotRuntimeProtocolError(
                "runtime returned an invalid camera mount status"
            )

        return cast(
            dict[str, float | None],
            result,
        )

    def battery_voltage(
        self,
    ) -> float:
        """Return the current robot battery voltage."""

        response = self._request("battery")

        result = response.result

        if not isinstance(
            result,
            dict,
        ):
            raise RobotRuntimeProtocolError(
                "runtime returned an invalid battery response"
            )

        data = cast(
            dict[object, object],
            result,
        )

        voltage = data.get("voltage")

        if isinstance(voltage, bool) or not isinstance(
            voltage,
            int | float,
        ):
            raise RobotRuntimeProtocolError("runtime battery voltage must be a number")

        return float(voltage)

    def grayscale_values(
        self,
    ) -> tuple[int, int, int]:
        """Return the current grayscale sensor values."""

        response = self._request("grayscale")

        result = response.result

        if not isinstance(
            result,
            dict,
        ):
            raise RobotRuntimeProtocolError(
                "runtime returned an invalid grayscale response"
            )

        data = cast(
            dict[object, object],
            result,
        )

        left = data.get("left")
        middle = data.get("middle")
        right = data.get("right")

        for name, value in (
            ("left", left),
            ("middle", middle),
            ("right", right),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise RobotRuntimeProtocolError(
                    f"runtime grayscale {name} must be an integer"
                )

        return (
            _integer_result(data, "left"),
            _integer_result(data, "middle"),
            _integer_result(data, "right"),
        )

    def ultrasonic_distance(
        self,
        samples: int = 10,
    ) -> float:
        """Return the current ultrasonic distance in centimeters."""

        if samples <= 0:
            raise ValueError("samples must be greater than zero")

        response = self._request(
            "ultrasonic",
            params={
                "samples": samples,
            },
        )

        result = response.result

        if not isinstance(
            result,
            dict,
        ):
            raise RobotRuntimeProtocolError(
                "runtime returned an invalid ultrasonic response"
            )

        data = cast(
            dict[object, object],
            result,
        )

        distance = data.get("distance_cm")

        if isinstance(distance, bool) or not isinstance(
            distance,
            int | float,
        ):
            raise RobotRuntimeProtocolError(
                "runtime ultrasonic distance must be a number"
            )

        return float(distance)

    def control(
        self,
        owner: str,
    ) -> RobotRuntimeControl:
        """Create a managed robot control session."""

        return RobotRuntimeControl(
            self,
            owner,
        )

    def drive_stop(
        self,
        token: str,
    ) -> None:
        """Stop the robot drive subsystem."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "drive_stop",
            params={
                "token": token,
            },
        )

    def steering_center(
        self,
        token: str,
    ) -> None:
        """Center the robot steering."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "steering_center",
            params={
                "token": token,
            },
        )

    def steering_left(
        self,
        token: str,
        angle: float = 30,
    ) -> None:
        """Turn the robot steering left."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "steering_left",
            params={
                "token": token,
                "angle": float(angle),
            },
        )

    def steering_right(
        self,
        token: str,
        angle: float = 30,
    ) -> None:
        """Turn the robot steering right."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "steering_right",
            params={
                "token": token,
                "angle": float(angle),
            },
        )

    def steering_angle(
        self,
        token: str,
        angle: float,
    ) -> None:
        """Set the robot steering angle."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "steering_angle",
            params={
                "token": token,
                "angle": float(angle),
            },
        )

    def drive_forward(
        self,
        token: str,
        speed: float = 20,
    ) -> None:
        """Drive the robot forward."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "drive_forward",
            params={
                "token": token,
                "speed": float(speed),
            },
        )

    def drive_backward(
        self,
        token: str,
        speed: float = 20,
    ) -> None:
        """Drive the robot backward."""

        if not token:
            raise ValueError("token cannot be empty")

        _ = self._request(
            "drive_backward",
            params={
                "token": token,
                "speed": float(speed),
            },
        )

    def camera_pan(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        _ = self._request(
            "camera_pan",
            params={
                "token": token,
                "angle": float(angle),
                "smooth": smooth,
            },
        )

    def camera_tilt(
        self,
        token: str,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        _ = self._request(
            "camera_tilt",
            params={
                "token": token,
                "angle": float(angle),
                "smooth": smooth,
            },
        )

    def camera_center(
        self,
        token: str,
        *,
        smooth: bool = True,
    ) -> None:
        _ = self._request(
            "camera_center",
            params={
                "token": token,
                "smooth": smooth,
            },
        )

    def preview_steering_calibration(
        self,
        token: str,
        offset: float,
    ) -> None:
        _ = self._request(
            "calibration_steering_preview",
            params={
                "token": token,
                "offset": float(offset),
            },
        )

    def preview_camera_calibration(
        self,
        token: str,
        *,
        pan_offset: float,
        tilt_offset: float,
    ) -> None:
        _ = self._request(
            "calibration_camera_preview",
            params={
                "token": token,
                "pan_offset": float(pan_offset),
                "tilt_offset": float(tilt_offset),
            },
        )

    def preview_motor_calibration(
        self,
        token: str,
        *,
        left_trim: float,
        right_trim: float,
        steering_offset: float,
    ) -> None:
        _ = self._request(
            "calibration_motor_preview",
            params={
                "token": token,
                "left_trim": float(left_trim),
                "right_trim": float(right_trim),
                "steering_offset": float(steering_offset),
            },
        )

    def _request(
        self,
        command: RuntimeCommand,
        *,
        params: dict[str, object] | None = None,
    ) -> RuntimeResponse:
        request = RuntimeRequest(
            version=PROTOCOL_VERSION,
            command=command,
            params={} if params is None else params,
        )

        data = self._exchange(
            encode_request(request),
        )

        try:
            response = decode_response(data)
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise RobotRuntimeProtocolError(f"invalid runtime response: {exc}") from exc

        if not response.ok:
            raise RobotRuntimeError(response.error or "runtime request failed")

        return response

    def _exchange(
        self,
        request: bytes,
    ) -> bytes:
        try:
            with socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            ) as client:
                client.settimeout(self.timeout)

                self._connect(client)

                client.sendall(request)

                data = bytearray()

                while True:
                    chunk = client.recv(4096)

                    if not chunk:
                        break

                    data.extend(chunk)

                    if len(data) > RESPONSE_LIMIT:
                        raise RobotRuntimeProtocolError("runtime response is too large")

                    if b"\n" in chunk:
                        break

        except RobotRuntimeUnavailableError:
            raise

        except (
            TimeoutError,
            OSError,
        ) as exc:
            raise RobotRuntimeUnavailableError(
                f"Betabox Robot Runtime is unavailable: {exc}"
            ) from exc

        if not data:
            raise RobotRuntimeProtocolError("runtime returned an empty response")

        line, _, _ = bytes(data).partition(b"\n")

        return line
