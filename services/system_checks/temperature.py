from __future__ import annotations

from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

from .models import TemperatureStatus
from .validation import (
    validate_config,
    validate_path,
)

TEMPERATURE_PATH = Path("/sys/class/thermal/thermal_zone0/temp")


def collect_temperature_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
    *,
    path: str | Path = TEMPERATURE_PATH,
) -> TemperatureStatus:
    """
    Collect the Raspberry Pi CPU temperature status.
    """

    config_value = validate_config(config)
    path_value = validate_path(
        path,
        name="path",
    )

    try:
        raw = path_value.read_text(encoding="utf-8").strip()
        celsius = float(raw) / 1000.0

    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        return TemperatureStatus(
            celsius=None,
            state="unknown",
            error=str(exc),
        )

    thresholds = config_value.health.temperature

    if celsius >= thresholds.critical_celsius:
        state = "critical"
    elif celsius >= thresholds.high_celsius:
        state = "high"
    else:
        state = "normal"

    return TemperatureStatus(
        celsius=celsius,
        state=state,
    )
