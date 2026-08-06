from __future__ import annotations

import re
from pathlib import Path

from betabox_robotics.config import PlatformConfig

_BACKUP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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


def validate_backup_name(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("backup name must be a string")

    result = value.strip()

    if not result:
        raise ValueError("backup name cannot be empty")

    if result in {
        ".",
        "..",
    }:
        raise ValueError("backup name is invalid")

    if not _BACKUP_NAME_PATTERN.fullmatch(result):
        raise ValueError(
            "backup name may contain only "
            "letters, numbers, periods, "
            "underscores, and hyphens"
        )

    return result
