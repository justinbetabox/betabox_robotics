from __future__ import annotations

import shutil
from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

from .models import DiskStatus
from .validation import (
    validate_config,
    validate_path,
)


def collect_disk_status(
    path: str | Path | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> DiskStatus:
    """
    Collect disk usage for the configured path and classify its health state.
    """

    config_value = validate_config(config)

    selected_path = config_value.health.disk_path if path is None else path

    path_value = validate_path(
        selected_path,
        name="path",
    )

    try:
        usage = shutil.disk_usage(path_value)

        if usage.total <= 0:
            raise ValueError("disk total must be greater than 0")

        used = usage.total - usage.free
        used_percent = used / usage.total * 100.0

    except (
        OSError,
        TypeError,
        ValueError,
        ZeroDivisionError,
    ) as exc:
        return DiskStatus(
            path=str(path_value),
            total_gb=None,
            free_gb=None,
            used_percent=None,
            state="unknown",
            error=str(exc),
        )

    thresholds = config_value.health.disk

    if used_percent >= thresholds.critical_percent:
        state = "critical"
    elif used_percent >= thresholds.high_percent:
        state = "high"
    else:
        state = "normal"

    gb = 1024**3

    return DiskStatus(
        path=str(path_value),
        total_gb=round(
            usage.total / gb,
            1,
        ),
        free_gb=round(
            usage.free / gb,
            1,
        ),
        used_percent=round(
            used_percent,
            1,
        ),
        state=state,
    )
