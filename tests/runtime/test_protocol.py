from __future__ import annotations

import json
import unittest

from betabox_robotics.runtime.protocol import (
    PROTOCOL_VERSION,
    RUNTIME_COMMANDS,
    RuntimeRequest,
    RuntimeResponse,
    RuntimeStatus,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)


class RuntimeRequestTests(unittest.TestCase):
    def test_to_dict_without_params(self) -> None:
        request = RuntimeRequest(
            version=PROTOCOL_VERSION,
            command="ping",
        )

        self.assertEqual(
            request.to_dict(),
            {
                "version": PROTOCOL_VERSION,
                "command": "ping",
                "params": {},
            },
        )

    def test_to_dict_copies_params(self) -> None:
        params: dict[str, object] = {
            "speed": 20.0,
        }

        request = RuntimeRequest(
            version=PROTOCOL_VERSION,
            command="drive_forward",
            params=params,
        )

        result = request.to_dict()

        self.assertEqual(
            result,
            {
                "version": PROTOCOL_VERSION,
                "command": "drive_forward",
                "params": {
                    "speed": 20.0,
                },
            },
        )

        self.assertIsNot(
            result["params"],
            params,
        )

    def test_encode_request(self) -> None:
        request = RuntimeRequest(
            version=PROTOCOL_VERSION,
            command="camera_pan",
            params={
                "token": "abc",
                "angle": 15.0,
                "smooth": True,
            },
        )

        encoded = encode_request(request)

        self.assertEqual(
            encoded,
            (
                b'{"version":1,"command":"camera_pan",'
                b'"params":{"token":"abc","angle":15.0,"smooth":true}}\n'
            ),
        )

    def test_decode_request(self) -> None:
        request = decode_request(
            (
                b'{"version":1,"command":"drive_forward",'
                b'"params":{"token":"abc","speed":20.0}}'
            ),
        )

        self.assertEqual(
            request,
            RuntimeRequest(
                version=PROTOCOL_VERSION,
                command="drive_forward",
                params={
                    "token": "abc",
                    "speed": 20.0,
                },
            ),
        )

    def test_decode_request_defaults_missing_params(self) -> None:
        request = decode_request(
            b'{"version":1,"command":"ping"}',
        )

        self.assertEqual(
            request.params,
            {},
        )

    def test_every_runtime_command_decodes(self) -> None:
        for command in RUNTIME_COMMANDS:
            with self.subTest(
                command=command,
            ):
                payload = json.dumps(
                    {
                        "version": PROTOCOL_VERSION,
                        "command": command,
                        "params": {},
                    }
                ).encode("utf-8")

                request = decode_request(payload)

                self.assertEqual(
                    request.command,
                    command,
                )

    def test_decode_request_rejects_invalid_utf8(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "invalid runtime request",
        ):
            _ = decode_request(
                b"\xff",
            )

    def test_decode_request_rejects_invalid_json(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "invalid runtime request",
        ):
            _ = decode_request(
                b"{",
            )

    def test_decode_request_rejects_non_object(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime request must be an object",
        ):
            _ = decode_request(
                b"[]",
            )

    def test_decode_request_rejects_missing_version(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime request version must be an integer",
        ):
            _ = decode_request(
                b'{"command":"ping"}',
            )

    def test_decode_request_rejects_boolean_version(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime request version must be an integer",
        ):
            _ = decode_request(
                b'{"version":true,"command":"ping"}',
            )

    def test_decode_request_rejects_unsupported_version(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unsupported runtime protocol version",
        ):
            _ = decode_request(
                b'{"version":999,"command":"ping"}',
            )

    def test_decode_request_rejects_non_string_command(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime request command must be a string",
        ):
            _ = decode_request(
                b'{"version":1,"command":1}',
            )

    def test_decode_request_rejects_unknown_command(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unknown runtime command",
        ):
            _ = decode_request(
                b'{"version":1,"command":"unknown"}',
            )

    def test_decode_request_rejects_non_object_params(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime request params must be an object",
        ):
            _ = decode_request(
                b'{"version":1,"command":"ping","params":[]}',
            )


class RuntimeResponseTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        response = RuntimeResponse(
            version=PROTOCOL_VERSION,
            ok=True,
            result={
                "ready": True,
            },
        )

        self.assertEqual(
            response.to_dict(),
            {
                "version": PROTOCOL_VERSION,
                "ok": True,
                "result": {
                    "ready": True,
                },
                "error": None,
            },
        )

    def test_encode_response(self) -> None:
        response = RuntimeResponse(
            version=PROTOCOL_VERSION,
            ok=False,
            error="failed",
        )

        self.assertEqual(
            encode_response(response),
            b'{"version":1,"ok":false,"result":null,"error":"failed"}\n',
        )

    def test_decode_success_response(self) -> None:
        response = decode_response(
            b'{"version":1,"ok":true,"result":"pong","error":null}',
        )

        self.assertEqual(
            response,
            RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=True,
                result="pong",
                error=None,
            ),
        )

    def test_decode_error_response(self) -> None:
        response = decode_response(
            b'{"version":1,"ok":false,"result":null,"error":"busy"}',
        )

        self.assertEqual(
            response,
            RuntimeResponse(
                version=PROTOCOL_VERSION,
                ok=False,
                result=None,
                error="busy",
            ),
        )

    def test_decode_response_rejects_invalid_json(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "invalid runtime response",
        ):
            _ = decode_response(
                b"{",
            )

    def test_decode_response_rejects_non_object(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime response must be an object",
        ):
            _ = decode_response(
                b"[]",
            )

    def test_decode_response_rejects_boolean_version(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime response version must be an integer",
        ):
            _ = decode_response(
                b'{"version":true,"ok":true}',
            )

    def test_decode_response_rejects_unsupported_version(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unsupported runtime protocol version",
        ):
            _ = decode_response(
                b'{"version":999,"ok":true}',
            )

    def test_decode_response_rejects_non_boolean_ok(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime response ok must be a boolean",
        ):
            _ = decode_response(
                b'{"version":1,"ok":1}',
            )

    def test_decode_response_rejects_non_string_error(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "runtime response error must be a string or None",
        ):
            _ = decode_response(
                b'{"version":1,"ok":false,"error":123}',
            )


class RuntimeStatusTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        status = RuntimeStatus(
            ready=True,
            ownership_acquired=True,
            hardware_initialized=True,
            control_owner="Test Client",
            pid=1234,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "ready": True,
                "ownership_acquired": True,
                "hardware_initialized": True,
                "control_owner": "Test Client",
                "pid": 1234,
            },
        )

    def test_to_dict_without_control_owner(self) -> None:
        status = RuntimeStatus(
            ready=True,
            ownership_acquired=True,
            hardware_initialized=True,
            control_owner=None,
            pid=1234,
        )

        self.assertIsNone(
            status.to_dict()["control_owner"],
        )


if __name__ == "__main__":
    _ = unittest.main()
