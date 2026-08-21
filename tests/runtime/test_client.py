from __future__ import annotations

import unittest
from collections.abc import Callable
from pathlib import Path
from typing import cast, final
from unittest.mock import patch

from betabox_robotics.runtime.client import (
    DEFAULT_TIMEOUT,
    RobotRuntimeClient,
)
from betabox_robotics.runtime.control import RobotRuntimeControl
from betabox_robotics.runtime.errors import (
    RobotRuntimeError,
    RobotRuntimeProtocolError,
)
from betabox_robotics.runtime.protocol import (
    PROTOCOL_VERSION,
    RuntimeResponse,
    encode_response,
)


def _client() -> RobotRuntimeClient:
    return RobotRuntimeClient()


@final
class RobotRuntimeClientInitTests(unittest.TestCase):
    def test_defaults(self) -> None:
        client = RobotRuntimeClient()

        self.assertEqual(
            client.timeout,
            DEFAULT_TIMEOUT,
        )

    def test_custom_values(self) -> None:
        socket_path = Path("/tmp/test-runtime.sock")

        client = RobotRuntimeClient(
            socket_path=socket_path,
            timeout=5,
        )

        self.assertEqual(
            client.socket_path,
            socket_path,
        )
        self.assertEqual(
            client.timeout,
            5.0,
        )

    def test_rejects_zero_timeout(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "timeout must be greater than zero",
        ):
            _ = RobotRuntimeClient(
                timeout=0,
            )

    def test_rejects_negative_timeout(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "timeout must be greater than zero",
        ):
            _ = RobotRuntimeClient(
                timeout=-1,
            )


@final
class RobotRuntimeClientRequestTests(unittest.TestCase):
    def test_ping(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result="pong",
            ),
        ) as request:
            self.assertTrue(client.ping())

        request.assert_called_once_with("ping")

    def test_ping_rejects_invalid_response(self) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result="wrong",
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "invalid ping response",
            ),
        ):
            _ = client.ping()

    def test_acquire_control(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "token": "test-token",
                },
            ),
        ) as request:
            token = client.acquire_control("  Test Client  ")

        self.assertEqual(
            token,
            "test-token",
        )

        request.assert_called_once_with(
            "acquire_control",
            params={
                "owner": "Test Client",
            },
        )

    def test_acquire_control_rejects_empty_owner(
        self,
    ) -> None:
        client = _client()

        with self.assertRaisesRegex(
            ValueError,
            "owner cannot be empty",
        ):
            _ = client.acquire_control("   ")

    def test_acquire_control_rejects_non_object_response(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result="invalid",
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "invalid control response",
            ),
        ):
            _ = client.acquire_control("Test")

    def test_acquire_control_rejects_non_string_token(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result={
                        "token": 123,
                    },
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "control token must be a string",
            ),
        ):
            _ = client.acquire_control("Test")

    def test_acquire_control_rejects_empty_token(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result={
                        "token": "",
                    },
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "control token cannot be empty",
            ),
        ):
            _ = client.acquire_control("Test")

    def test_release_control(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
            ),
        ) as request:
            client.release_control("token")

        request.assert_called_once_with(
            "release_control",
            params={
                "token": "token",
            },
        )

    def test_release_control_rejects_empty_token(
        self,
    ) -> None:
        client = _client()

        with self.assertRaisesRegex(
            ValueError,
            "token cannot be empty",
        ):
            client.release_control("")

    def test_renew_control(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
            ),
        ) as request:
            client.renew_control("token")

        request.assert_called_once_with(
            "renew_control",
            params={
                "token": "token",
            },
        )

    def test_control_returns_managed_session(
        self,
    ) -> None:
        client = _client()

        control = client.control("Test Client")

        self.assertIsInstance(
            control,
            RobotRuntimeControl,
        )
        self.assertIs(
            control.client,
            client,
        )
        self.assertEqual(
            control.owner,
            "Test Client",
        )


@final
class RobotRuntimeClientStatusTests(unittest.TestCase):
    def test_status(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "ready": True,
                    "ownership_acquired": True,
                    "hardware_initialized": True,
                    "control_owner": "Test",
                    "pid": 1234,
                },
            ),
        ):
            status = client.status()

        self.assertTrue(status.ready)
        self.assertTrue(status.ownership_acquired)
        self.assertTrue(status.hardware_initialized)
        self.assertEqual(
            status.control_owner,
            "Test",
        )
        self.assertEqual(
            status.pid,
            1234,
        )

    def test_status_accepts_no_control_owner(
        self,
    ) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "ready": True,
                    "ownership_acquired": True,
                    "hardware_initialized": True,
                    "control_owner": None,
                    "pid": 1234,
                },
            ),
        ):
            status = client.status()

        self.assertIsNone(status.control_owner)

    def test_status_rejects_non_object(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result=None,
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "invalid status response",
            ),
        ):
            _ = client.status()

    def test_status_rejects_invalid_ready(
        self,
    ) -> None:
        self._assert_invalid_status(
            "ready",
            1,
            "ready must be a boolean",
        )

    def test_status_rejects_invalid_ownership(
        self,
    ) -> None:
        self._assert_invalid_status(
            "ownership_acquired",
            1,
            "ownership_acquired must be a boolean",
        )

    def test_status_rejects_invalid_hardware_initialized(
        self,
    ) -> None:
        self._assert_invalid_status(
            "hardware_initialized",
            1,
            "hardware_initialized must be a boolean",
        )

    def test_status_rejects_invalid_control_owner(
        self,
    ) -> None:
        self._assert_invalid_status(
            "control_owner",
            1,
            "control_owner must be a string or None",
        )

    def test_status_rejects_invalid_pid(
        self,
    ) -> None:
        self._assert_invalid_status(
            "pid",
            True,
            "pid must be an integer",
        )

    def _assert_invalid_status(
        self,
        key: str,
        value: object,
        message: str,
    ) -> None:
        client = _client()

        result: dict[str, object] = {
            "ready": True,
            "ownership_acquired": True,
            "hardware_initialized": True,
            "control_owner": None,
            "pid": 1234,
        }
        result[key] = value

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result=result,
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                message,
            ),
        ):
            _ = client.status()


@final
class RobotRuntimeClientSensorTests(unittest.TestCase):
    def test_battery_voltage(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "voltage": 8.25,
                },
            ),
        ):
            self.assertEqual(
                client.battery_voltage(),
                8.25,
            )

    def test_battery_voltage_accepts_integer(
        self,
    ) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "voltage": 8,
                },
            ),
        ):
            self.assertEqual(
                client.battery_voltage(),
                8.0,
            )

    def test_battery_rejects_boolean_voltage(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result={
                        "voltage": True,
                    },
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "battery voltage must be a number",
            ),
        ):
            _ = client.battery_voltage()

    def test_grayscale_values(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "left": 100,
                    "middle": 200,
                    "right": 300,
                },
            ),
        ):
            self.assertEqual(
                client.grayscale_values(),
                (
                    100,
                    200,
                    300,
                ),
            )

    def test_grayscale_rejects_boolean_value(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result={
                        "left": True,
                        "middle": 200,
                        "right": 300,
                    },
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "grayscale left must be an integer",
            ),
        ):
            _ = client.grayscale_values()

    def test_ultrasonic_distance(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "distance_cm": 42.5,
                },
            ),
        ) as request:
            distance = client.ultrasonic_distance(3)

        self.assertEqual(
            distance,
            42.5,
        )

        request.assert_called_once_with(
            "ultrasonic",
            params={
                "samples": 3,
            },
        )

    def test_ultrasonic_rejects_zero_samples(
        self,
    ) -> None:
        client = _client()

        with self.assertRaisesRegex(
            ValueError,
            "samples must be greater than zero",
        ):
            _ = client.ultrasonic_distance(0)

    def test_ultrasonic_rejects_invalid_distance(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_request",
                return_value=RuntimeResponse(
                    version=PROTOCOL_VERSION,
                    ok=True,
                    result={
                        "distance_cm": True,
                    },
                ),
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "ultrasonic distance must be a number",
            ),
        ):
            _ = client.ultrasonic_distance()


@final
class RobotRuntimeClientDriveTests(unittest.TestCase):
    def test_drive_status(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result={
                    "closed": False,
                    "left_trim": 1.0,
                    "right_trim": 0.9,
                    "steering_offset": 2.5,
                },
            ),
        ):
            status = client.drive_status()

        self.assertEqual(
            status,
            {
                "closed": False,
                "left_trim": 1.0,
                "right_trim": 0.9,
                "steering_offset": 2.5,
            },
        )

    def test_drive_forward_request(self) -> None:
        self._assert_command(
            method="drive_forward",
            args=(
                "token",
                25,
            ),
            command="drive_forward",
            params={
                "token": "token",
                "speed": 25.0,
            },
        )

    def test_drive_backward_request(self) -> None:
        self._assert_command(
            method="drive_backward",
            args=(
                "token",
                25,
            ),
            command="drive_backward",
            params={
                "token": "token",
                "speed": 25.0,
            },
        )

    def test_drive_stop_request(self) -> None:
        self._assert_command(
            method="drive_stop",
            args=("token",),
            command="drive_stop",
            params={
                "token": "token",
            },
        )

    def test_steering_left_request(self) -> None:
        self._assert_command(
            method="steering_left",
            args=(
                "token",
                15,
            ),
            command="steering_left",
            params={
                "token": "token",
                "angle": 15.0,
            },
        )

    def test_steering_right_request(self) -> None:
        self._assert_command(
            method="steering_right",
            args=(
                "token",
                15,
            ),
            command="steering_right",
            params={
                "token": "token",
                "angle": 15.0,
            },
        )

    def test_steering_center_request(self) -> None:
        self._assert_command(
            method="steering_center",
            args=("token",),
            command="steering_center",
            params={
                "token": "token",
            },
        )

    def test_steering_angle_request(self) -> None:
        self._assert_command(
            method="steering_angle",
            args=(
                "token",
                -12.5,
            ),
            command="steering_angle",
            params={
                "token": "token",
                "angle": -12.5,
            },
        )

    def _assert_command(
        self,
        *,
        method: str,
        args: tuple[object, ...],
        command: str,
        params: dict[str, object],
    ) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
            ),
        ) as request:
            callback = cast(
                Callable[..., None],
                getattr(
                    client,
                    method,
                ),
            )

            callback(*args)

        request.assert_called_once_with(
            command,
            params=params,
        )


@final
class RobotRuntimeClientCameraTests(unittest.TestCase):
    def test_camera_mount_status(self) -> None:
        client = _client()

        result = {
            "pan": 10.0,
            "tilt": -5.0,
            "pan_offset": 1.0,
            "tilt_offset": 2.0,
            "pan_min": -45.0,
            "pan_max": 45.0,
            "tilt_min": -30.0,
            "tilt_max": 45.0,
        }

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result=result,
            ),
        ):
            self.assertEqual(
                client.camera_mount_status(),
                result,
            )

    def test_camera_pan_request(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
            ),
        ) as request:
            client.camera_pan(
                "token",
                15,
                smooth=False,
            )

        request.assert_called_once_with(
            "camera_pan",
            params={
                "token": "token",
                "angle": 15.0,
                "smooth": False,
            },
        )

    def test_camera_tilt_request(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
            ),
        ) as request:
            client.camera_tilt(
                "token",
                -10,
            )

        request.assert_called_once_with(
            "camera_tilt",
            params={
                "token": "token",
                "angle": -10.0,
                "smooth": True,
            },
        )

    def test_camera_center_request(self) -> None:
        client = _client()

        with patch.object(
            client,
            "_request",
            return_value=RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
            ),
        ) as request:
            client.camera_center(
                "token",
                smooth=False,
            )

        request.assert_called_once_with(
            "camera_center",
            params={
                "token": "token",
                "smooth": False,
            },
        )


@final
class RobotRuntimeClientResponseHandlingTests(unittest.TestCase):
    def test_ping_decodes_success_response(
        self,
    ) -> None:
        client = _client()

        response_data = encode_response(
            RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result="pong",
            )
        )

        with patch.object(
            client,
            "_exchange",
            return_value=response_data,
        ) as exchange:
            self.assertTrue(client.ping())

        sent = cast(
            bytes,
            exchange.call_args.args[0],
        )

        self.assertIn(
            b'"command":"ping"',
            sent,
        )
        self.assertIn(
            b'"params":{}',
            sent,
        )

    def test_runtime_error_response_raises(
        self,
    ) -> None:
        client = _client()

        response_data = encode_response(
            RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=False,
                error="busy",
            )
        )

        with (
            patch.object(
                client,
                "_exchange",
                return_value=response_data,
            ),
            self.assertRaisesRegex(
                RobotRuntimeError,
                "busy",
            ),
        ):
            _ = client.ping()

    def test_runtime_error_uses_fallback_message(
        self,
    ) -> None:
        client = _client()

        response_data = encode_response(
            RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=False,
                error=None,
            )
        )

        with (
            patch.object(
                client,
                "_exchange",
                return_value=response_data,
            ),
            self.assertRaisesRegex(
                RobotRuntimeError,
                "runtime request failed",
            ),
        ):
            _ = client.ping()

    def test_invalid_response_is_wrapped(
        self,
    ) -> None:
        client = _client()

        with (
            patch.object(
                client,
                "_exchange",
                return_value=b"{",
            ),
            self.assertRaisesRegex(
                RobotRuntimeProtocolError,
                "invalid runtime response",
            ),
        ):
            _ = client.ping()


if __name__ == "__main__":
    _ = unittest.main()
