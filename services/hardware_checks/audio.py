from __future__ import annotations

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run

from .models import AudioStatus


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def collect_audio_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> AudioStatus:
    """
    Collect the current audio-device status.
    """

    config_value = _validate_config(config)

    result = run(
        [
            "aplay",
            "-l",
        ],
        timeout=(config_value.verification.command_timeout_seconds),
    )

    if result is None:
        return AudioStatus(
            available=False,
            device=None,
            error="could not run aplay",
        )

    output = result.stdout + result.stderr

    if result.returncode != 0:
        return AudioStatus(
            available=False,
            device=None,
            error=(output.strip() or "aplay failed"),
        )

    detected = any(
        identifier in output
        for identifier in (config_value.verification.hifiberry_identifiers)
    )

    if detected:
        return AudioStatus(
            available=True,
            device="HifiBerry DAC",
        )

    return AudioStatus(
        available=False,
        device=None,
        error=("HifiBerry audio device was not detected"),
    )
