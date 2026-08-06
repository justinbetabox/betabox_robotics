from __future__ import annotations

from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

from .models import CheckResult
from .validation import (
    validate_config,
    validate_path,
)


def check_media_path(
    path: str | Path,
) -> CheckResult:
    """
    Verify that one configured media directory exists.
    """

    path_value = validate_path(
        path,
        name="path",
    )
    check_name = f"media:{path_value.name}"

    try:
        exists = path_value.exists()
    except OSError as exc:
        return CheckResult(
            name=check_name,
            ok=False,
            message=str(exc),
        )

    return CheckResult(
        name=check_name,
        ok=exists,
        message=(str(path_value) if exists else f"missing {path_value}"),
    )


def check_media_paths(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[CheckResult, ...]:
    """
    Verify the configured pictures, videos, and sounds
    directories.
    """

    config_value = validate_config(config)

    paths = (
        config_value.paths.pictures_dir,
        config_value.paths.videos_dir,
        config_value.paths.sounds_dir,
    )

    return tuple(check_media_path(path) for path in paths)
