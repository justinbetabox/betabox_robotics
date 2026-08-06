from __future__ import annotations

from pathlib import Path

from betabox_robotics.config import PlatformConfig


def validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


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


def validate_interface_name(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("name must be a string")

    result = value.strip()

    if not result:
        raise ValueError("name cannot be empty")

    return result
