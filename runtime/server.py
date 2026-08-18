from __future__ import annotations

import grp
import os
import socket
from pathlib import Path

from betabox_robotics.sensors import SensorError

from .errors import RobotRuntimeError
from .protocol import (
    PROTOCOL_VERSION,
    RUNTIME_SOCKET_GROUP,
    RUNTIME_SOCKET_MODE,
    RUNTIME_SOCKET_PATH,
    RuntimeRequest,
    RuntimeResponse,
    decode_request,
    encode_response,
)
from .runtime import RobotRuntime

REQUEST_LIMIT = 64 * 1024

RUNTIME_POLL_INTERVAL = 0.1


class RobotRuntimeServer:
    """Local Unix-socket server for the Betabox robot runtime."""

    runtime: RobotRuntime
    socket_path: Path

    _socket: socket.socket | None
    _running: bool

    def __init__(
        self,
        runtime: RobotRuntime | None = None,
        *,
        socket_path: Path = RUNTIME_SOCKET_PATH,
    ) -> None:
        self.runtime = runtime if runtime is not None else RobotRuntime()
        self.socket_path = Path(socket_path)

        self._socket = None
        self._running = False

    @staticmethod
    def _string_param(
        request: RuntimeRequest,
        name: str,
    ) -> str:
        value = request.params.get(name)

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(f"runtime parameter {name} must be a string")

        result = value.strip()

        if not result:
            raise ValueError(f"runtime parameter {name} cannot be empty")

        return result

    @staticmethod
    def _number_param(
        request: RuntimeRequest,
        name: str,
    ) -> float:
        value = request.params.get(name)

        if isinstance(value, bool) or not isinstance(
            value,
            int | float,
        ):
            raise TypeError(f"runtime parameter {name} must be a number")

        return float(value)

    @staticmethod
    def _integer_param(
        request: RuntimeRequest,
        name: str,
        *,
        default: int | None = None,
    ) -> int:
        value = request.params.get(name)

        if value is None and default is not None:
            return default

        if isinstance(value, bool) or not isinstance(
            value,
            int,
        ):
            raise TypeError(f"runtime parameter {name} must be an integer")

        return value

    @staticmethod
    def _boolean_param(
        request: RuntimeRequest,
        name: str,
        *,
        default: bool | None = None,
    ) -> bool:
        value = request.params.get(name)

        if value is None and default is not None:
            return default

        if not isinstance(
            value,
            bool,
        ):
            raise TypeError(f"runtime parameter {name} must be a boolean")

        return value

    @property
    def running(
        self,
    ) -> bool:
        return self._running

    def start(
        self,
    ) -> None:
        """Start the runtime and bind the local socket."""

        if self._running:
            return

        self.runtime.start()

        try:
            self._prepare_socket_directory()
            self._remove_stale_socket()

            server_socket = socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            )

            try:
                server_socket.bind(str(self.socket_path))
                self._configure_socket_permissions()
                server_socket.listen()
                server_socket.settimeout(
                    RUNTIME_POLL_INTERVAL,
                )
            except (
                OSError,
                RuntimeError,
            ):
                server_socket.close()
                raise

            self._socket = server_socket
            self._running = True

        except (
            OSError,
            RuntimeError,
        ):
            self.runtime.stop()
            raise

    def serve_forever(
        self,
    ) -> None:
        """Serve requests until the server is stopped."""

        if not self._running:
            self.start()

        server_socket = self._socket

        if server_socket is None:
            raise RuntimeError("runtime server socket is not available")

        while self._running:
            try:
                connection = server_socket.accept()[0]

            except TimeoutError:
                self.runtime.poll()
                continue

            except OSError:
                if not self._running:
                    break

                raise

            with connection:
                self._serve_connection(connection)

            self.runtime.poll()

    def stop(
        self,
    ) -> None:
        """Stop the socket server and release robot ownership."""

        self._running = False

        server_socket = self._socket
        self._socket = None

        if server_socket is not None:
            server_socket.close()

        try:
            self._remove_stale_socket()
        finally:
            self.runtime.stop()

    def close(
        self,
    ) -> None:
        self.stop()

    def _serve_connection(
        self,
        connection: socket.socket,
    ) -> None:
        try:
            request = self._read_request(
                connection,
            )
            response = self._handle_request(
                request,
            )
        except (
            RobotRuntimeError,
            SensorError,
            TypeError,
            ValueError,
        ) as exc:
            response = RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=False,
                error=str(exc),
            )

        connection.sendall(
            encode_response(response),
        )

    def _read_request(
        self,
        connection: socket.socket,
    ) -> RuntimeRequest:
        data = bytearray()

        while True:
            chunk = connection.recv(4096)

            if not chunk:
                break

            data.extend(chunk)

            if len(data) > REQUEST_LIMIT:
                raise ValueError("runtime request is too large")

            if b"\n" in chunk:
                break

        if not data:
            raise ValueError("runtime request is empty")

        line, _, _ = bytes(data).partition(b"\n")

        return decode_request(line)

    def _handle_request(
        self,
        request: RuntimeRequest,
    ) -> RuntimeResponse:
        if request.command == "ping":
            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result="pong",
            )

        if request.command == "acquire_control":
            owner = self._string_param(
                request,
                "owner",
            )

            token = self.runtime.acquire_control(owner)

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "token": token,
                },
            )

        if request.command == "release_control":
            token = self._string_param(
                request,
                "token",
            )

            self.runtime.release_control(token)

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "renew_control":
            token = self._string_param(
                request,
                "token",
            )

            self.runtime.renew_control(token)

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "status":
            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=self.runtime.status().to_dict(),
            )

        if request.command == "battery":
            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "voltage": self.runtime.battery_voltage(),
                },
            )

        if request.command == "grayscale":
            values = self.runtime.grayscale_values()

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "left": values[0],
                    "middle": values[1],
                    "right": values[2],
                },
            )

        if request.command == "ultrasonic":
            samples = self._integer_param(
                request,
                "samples",
                default=10,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "distance_cm": self.runtime.ultrasonic_distance(
                        samples=samples,
                    ),
                },
            )

        if request.command == "drive_status":
            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=self.runtime.drive_status(),
            )

        if request.command == "drive_stop":
            token = self._string_param(
                request,
                "token",
            )

            self.runtime.drive_stop(token)

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "steering_center":
            token = self._string_param(
                request,
                "token",
            )

            self.runtime.steering_center(token)

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "steering_left":
            token = self._string_param(
                request,
                "token",
            )
            angle = self._number_param(
                request,
                "angle",
            )

            self.runtime.steering_left(
                token,
                angle=angle,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "steering_right":
            token = self._string_param(
                request,
                "token",
            )
            angle = self._number_param(
                request,
                "angle",
            )

            self.runtime.steering_right(
                token,
                angle=angle,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "steering_angle":
            token = self._string_param(
                request,
                "token",
            )
            angle = self._number_param(
                request,
                "angle",
            )

            self.runtime.steering_angle(
                token,
                angle,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "drive_forward":
            token = self._string_param(
                request,
                "token",
            )
            speed = self._number_param(
                request,
                "speed",
            )

            self.runtime.drive_forward(
                token,
                speed=speed,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "drive_backward":
            token = self._string_param(
                request,
                "token",
            )
            speed = self._number_param(
                request,
                "speed",
            )

            self.runtime.drive_backward(
                token,
                speed=speed,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "camera_mount_status":
            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=self.runtime.camera_mount_status(),
            )

        if request.command == "camera_pan":
            token = self._string_param(
                request,
                "token",
            )
            angle = self._number_param(
                request,
                "angle",
            )
            smooth = self._boolean_param(
                request,
                "smooth",
                default=True,
            )

            self.runtime.camera_pan(
                token,
                angle,
                smooth=smooth,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "camera_tilt":
            token = self._string_param(
                request,
                "token",
            )
            angle = self._number_param(
                request,
                "angle",
            )
            smooth = self._boolean_param(
                request,
                "smooth",
                default=True,
            )

            self.runtime.camera_tilt(
                token,
                angle,
                smooth=smooth,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "camera_center":
            token = self._string_param(
                request,
                "token",
            )
            smooth = self._boolean_param(
                request,
                "smooth",
                default=True,
            )

            self.runtime.camera_center(
                token,
                smooth=smooth,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "calibration_steering_preview":
            token = self._string_param(
                request,
                "token",
            )
            offset = self._number_param(
                request,
                "offset",
            )

            self.runtime.preview_steering_calibration(
                token,
                offset,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "calibration_camera_preview":
            token = self._string_param(
                request,
                "token",
            )
            pan_offset = self._number_param(
                request,
                "pan_offset",
            )
            tilt_offset = self._number_param(
                request,
                "tilt_offset",
            )

            self.runtime.preview_camera_calibration(
                token,
                pan_offset=pan_offset,
                tilt_offset=tilt_offset,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        if request.command == "calibration_motor_preview":
            token = self._string_param(
                request,
                "token",
            )
            left_trim = self._number_param(
                request,
                "left_trim",
            )
            right_trim = self._number_param(
                request,
                "right_trim",
            )
            steering_offset = self._number_param(
                request,
                "steering_offset",
            )

            self.runtime.preview_motor_calibration(
                token,
                left_trim=left_trim,
                right_trim=right_trim,
                steering_offset=steering_offset,
            )

            return RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=None,
            )

        raise ValueError(f"unsupported runtime command: {request.command}")

    def _prepare_socket_directory(
        self,
    ) -> None:
        directory = self.socket_path.parent

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _configure_socket_permissions(
        self,
    ) -> None:
        try:
            group = grp.getgrnam(RUNTIME_SOCKET_GROUP)
        except KeyError as exc:
            raise RuntimeError(
                f"Required Linux group does not exist: {RUNTIME_SOCKET_GROUP}"
            ) from exc

        os.chown(
            self.socket_path,
            -1,
            group.gr_gid,
        )
        os.chmod(
            self.socket_path,
            RUNTIME_SOCKET_MODE,
        )

    def _remove_stale_socket(
        self,
    ) -> None:
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            return
