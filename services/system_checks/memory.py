from __future__ import annotations

from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

from .models import MemoryStatus
from .validation import (
    validate_config,
    validate_path,
)

MEMINFO_PATH = Path("/proc/meminfo")


def collect_memory_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
    *,
    path: str | Path = MEMINFO_PATH,
) -> MemoryStatus:
    """
    Collect system memory usage and classify its health state.
    """

    config_value = validate_config(config)
    path_value = validate_path(
        path,
        name="path",
    )

    try:
        values: dict[str, int] = {}

        with path_value.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                key, separator, raw_value = line.partition(":")

                if not separator:
                    continue

                parts = raw_value.strip().split()

                if not parts:
                    continue

                values[key.strip()] = int(parts[0])

        total_kb = values["MemTotal"]
        available_kb = values["MemAvailable"]

        if total_kb <= 0:
            raise ValueError("MemTotal must be greater than 0")

        used_percent = (total_kb - available_kb) / total_kb * 100.0

    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        ZeroDivisionError,
    ) as exc:
        return MemoryStatus(
            total_mb=None,
            available_mb=None,
            used_percent=None,
            state="unknown",
            error=str(exc),
        )

    thresholds = config_value.health.memory

    if used_percent >= thresholds.critical_percent:
        state = "critical"
    elif used_percent >= thresholds.high_percent:
        state = "high"
    else:
        state = "normal"

    return MemoryStatus(
        total_mb=round(total_kb / 1024),
        available_mb=round(available_kb / 1024),
        used_percent=round(
            used_percent,
            1,
        ),
        state=state,
    )
