from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from betabox_robotics.config import PlatformConfig
from betabox_robotics.services.hardware_checks import (
    RobotHardwareStatus,
)

from .models import CheckResult


def validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def validate_path(
    value: object,
    *,
    name: str,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string or Path")

    return Path(value).expanduser()


def validate_timeout(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("timeout must be an integer")

    if value <= 0:
        raise ValueError("timeout must be greater than 0")

    return value


def validate_command(
    value: object,
) -> list[str]:
    if isinstance(
        value,
        str | bytes,
    ) or not isinstance(
        value,
        Sequence,
    ):
        raise TypeError("command must be a sequence of strings")

    result: list[str] = []

    for argument in value:
        if not isinstance(
            argument,
            str,
        ):
            raise TypeError("command must contain only strings")

        argument_value = argument.strip()

        if not argument_value:
            raise ValueError("command cannot contain empty strings")

        result.append(argument_value)

    if not result:
        raise ValueError("command cannot be empty")

    return result


def validate_include_robot(
    value: object,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError("include_robot must be a boolean")

    return value


def validate_hardware_status(
    value: object,
) -> RobotHardwareStatus:
    if not isinstance(
        value,
        RobotHardwareStatus,
    ):
        raise TypeError("hardware must be a RobotHardwareStatus")

    return value


def validate_checks(
    value: object,
) -> tuple[CheckResult, ...]:
    if not isinstance(
        value,
        tuple,
    ):
        raise TypeError("checks must be a tuple")

    if not all(isinstance(check, CheckResult) for check in value):
        raise TypeError("checks must contain only CheckResult values")

    return value
