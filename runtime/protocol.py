from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict, cast

PROTOCOL_VERSION = 1

RUNTIME_SOCKET_PATH = Path("/run/betabox/robot.sock")
RUNTIME_SOCKET_GROUP = "betabox"
RUNTIME_SOCKET_MODE = 0o660

RuntimeCommand = Literal[
    "ping",
    "status",
    "battery",
    "grayscale",
    "ultrasonic",
    "drive_status",
    "acquire_control",
    "release_control",
    "renew_control",
    "drive_forward",
    "drive_backward",
    "drive_stop",
    "steering_left",
    "steering_right",
    "steering_center",
    "steering_angle",
    "camera_mount_status",
    "camera_pan",
    "camera_tilt",
    "camera_center",
    "calibration_steering_preview",
    "calibration_camera_preview",
    "calibration_motor_preview",
]

RUNTIME_COMMANDS: frozenset[str] = frozenset(
    {
        "ping",
        "status",
        "battery",
        "grayscale",
        "ultrasonic",
        "drive_status",
        "acquire_control",
        "release_control",
        "renew_control",
        "drive_forward",
        "drive_backward",
        "drive_stop",
        "steering_left",
        "steering_right",
        "steering_center",
        "steering_angle",
        "camera_mount_status",
        "camera_pan",
        "camera_tilt",
        "camera_center",
        "calibration_steering_preview",
        "calibration_camera_preview",
        "calibration_motor_preview",
    }
)


class RuntimeRequestData(TypedDict):
    version: int
    command: str
    params: dict[str, object]


class RuntimeStatusData(TypedDict):
    ready: bool
    ownership_acquired: bool
    hardware_initialized: bool
    control_owner: str | None
    pid: int


class RuntimeResponseData(TypedDict):
    version: int
    ok: bool
    result: object | None
    error: str | None


@dataclass(frozen=True, slots=True)
class RuntimeRequest:
    version: int
    command: RuntimeCommand
    params: dict[str, object] = field(
        default_factory=dict,
    )

    def to_dict(
        self,
    ) -> RuntimeRequestData:
        return {
            "version": self.version,
            "command": self.command,
            "params": dict(self.params),
        }


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    ready: bool
    ownership_acquired: bool
    hardware_initialized: bool
    control_owner: str | None
    pid: int

    def to_dict(
        self,
    ) -> RuntimeStatusData:
        return {
            "ready": self.ready,
            "ownership_acquired": self.ownership_acquired,
            "hardware_initialized": self.hardware_initialized,
            "control_owner": self.control_owner,
            "pid": self.pid,
        }


@dataclass(frozen=True, slots=True)
class RuntimeResponse:
    version: int
    ok: bool
    result: object | None = None
    error: str | None = None

    def to_dict(
        self,
    ) -> RuntimeResponseData:
        return {
            "version": self.version,
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
        }


def encode_request(
    request: RuntimeRequest,
) -> bytes:
    return (
        json.dumps(
            request.to_dict(),
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def encode_response(
    response: RuntimeResponse,
) -> bytes:
    return (
        json.dumps(
            response.to_dict(),
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def decode_request(
    data: bytes,
) -> RuntimeRequest:
    try:
        raw = cast(
            object,
            json.loads(data.decode("utf-8")),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("invalid runtime request") from exc

    if not isinstance(
        raw,
        dict,
    ):
        raise TypeError("runtime request must be an object")

    value = cast(
        dict[object, object],
        raw,
    )

    version = value.get("version")
    command = value.get("command")
    params = value.get(
        "params",
        {},
    )

    if isinstance(version, bool) or not isinstance(
        version,
        int,
    ):
        raise TypeError("runtime request version must be an integer")

    if version != PROTOCOL_VERSION:
        raise ValueError(f"unsupported runtime protocol version: {version}")

    if not isinstance(
        command,
        str,
    ):
        raise TypeError("runtime request command must be a string")

    if command not in RUNTIME_COMMANDS:
        raise ValueError(f"unknown runtime command: {command}")

    if not isinstance(
        params,
        dict,
    ):
        raise TypeError("runtime request params must be an object")

    raw_params = cast(
        dict[object, object],
        params,
    )

    validated_params: dict[str, object] = {}

    for key, param_value in raw_params.items():
        if not isinstance(
            key,
            str,
        ):
            raise TypeError("runtime request parameter names must be strings")

        validated_params[key] = param_value

    return RuntimeRequest(
        version=version,
        command=cast(
            RuntimeCommand,
            command,
        ),
        params=validated_params,
    )


def decode_response(
    data: bytes,
) -> RuntimeResponse:
    try:
        raw = cast(
            object,
            json.loads(data.decode("utf-8")),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("invalid runtime response") from exc

    if not isinstance(
        raw,
        dict,
    ):
        raise TypeError("runtime response must be an object")

    value = cast(
        dict[object, object],
        raw,
    )

    version = value.get("version")
    ok = value.get("ok")
    result = value.get("result")
    error = value.get("error")

    if isinstance(version, bool) or not isinstance(
        version,
        int,
    ):
        raise TypeError("runtime response version must be an integer")

    if version != PROTOCOL_VERSION:
        raise ValueError(f"unsupported runtime protocol version: {version}")

    if not isinstance(
        ok,
        bool,
    ):
        raise TypeError("runtime response ok must be a boolean")

    if error is not None and not isinstance(
        error,
        str,
    ):
        raise TypeError("runtime response error must be a string or None")

    return RuntimeResponse(
        version=version,
        ok=ok,
        result=result,
        error=error,
    )
