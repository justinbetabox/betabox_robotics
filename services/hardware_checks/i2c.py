from __future__ import annotations

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run

from .models import I2CStatus


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def collect_i2c_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> I2CStatus:
    """
    Collect the current I2C bus and device status.
    """

    config_value = _validate_config(config)
    device = config_value.verification.i2c_device

    if not device.exists():
        return I2CStatus(
            available=False,
            devices=(),
            error=f"{device} is missing",
        )

    result = run(
        [
            "i2cdetect",
            "-y",
            str(config_value.verification.i2c_bus),
        ],
        timeout=(config_value.verification.command_timeout_seconds),
    )

    if result is None:
        return I2CStatus(
            available=True,
            devices=(),
            error="could not run i2cdetect",
        )

    if result.returncode != 0:
        message = result.stderr.strip() or "i2cdetect failed"

        return I2CStatus(
            available=True,
            devices=(),
            error=message,
        )

    devices: set[str] = set()

    for line in result.stdout.splitlines():
        if ":" not in line:
            continue

        _, values = line.split(
            ":",
            maxsplit=1,
        )

        for value in values.split():
            if value == "--":
                continue

            if len(value) != 2:
                continue

            try:
                int(
                    value,
                    16,
                )
            except ValueError:
                continue

            devices.add(f"0x{value.casefold()}")

    return I2CStatus(
        available=True,
        devices=tuple(sorted(devices)),
    )
