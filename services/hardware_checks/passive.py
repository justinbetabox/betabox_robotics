from __future__ import annotations

import math
from typing import Final

from betabox_robotics.robots.config import SensorsConfig
from betabox_robotics.runtime.client import RobotRuntimeClient
from betabox_robotics.runtime.errors import RobotRuntimeError

from .models import (
    BatteryStatus,
    SensorStatus,
)

GRAYSCALE_CHANNEL_COUNT: Final[int] = 3
GRAYSCALE_IMPLAUSIBLE_HIGH: Final[int] = 3000
GRAYSCALE_PLAUSIBILITY_SAMPLES: Final[int] = 5

ULTRASONIC_HEALTH_SAMPLES: Final[int] = 1


def _validate_sensors_config(
    value: object,
) -> SensorsConfig:
    if not isinstance(
        value,
        SensorsConfig,
    ):
        raise TypeError("sensors_config must be a SensorsConfig")

    return value


def _battery_state(
    voltage: float,
    *,
    low_voltage: float,
    critical_voltage: float,
) -> str:
    if voltage < critical_voltage:
        return "critical"

    if voltage < low_voltage:
        return "low"

    return "ok"


def _grayscale_plausibility(
    client: RobotRuntimeClient,
    first_values: tuple[int, int, int],
) -> tuple[
    bool,
    tuple[int, ...],
]:
    samples = [
        first_values,
    ]

    for _ in range(GRAYSCALE_PLAUSIBILITY_SAMPLES - 1):
        samples.append(client.grayscale_values())

    suspicious_channels = tuple(
        channel
        for channel in range(GRAYSCALE_CHANNEL_COUNT)
        if all(sample[channel] > GRAYSCALE_IMPLAUSIBLE_HIGH for sample in samples)
    )

    return (
        not suspicious_channels,
        suspicious_channels,
    )


def _ultrasonic_status(
    client: RobotRuntimeClient,
) -> tuple[
    bool,
    float | None,
    str | None,
]:
    try:
        distance = client.ultrasonic_distance(
            samples=ULTRASONIC_HEALTH_SAMPLES,
        )

        if not math.isfinite(distance):
            raise ValueError("ultrasonic distance must be finite")

        if distance < 0:
            raise ValueError(f"invalid ultrasonic distance: {distance}")

        return (
            True,
            distance,
            None,
        )

    except (
        RobotRuntimeError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        return (
            False,
            None,
            str(exc),
        )


def collect_battery_status(
    sensors_config: SensorsConfig,
) -> BatteryStatus:
    """
    Collect battery status through the centralized robot runtime.
    """

    config_value = _validate_sensors_config(sensors_config)

    try:
        voltage = RobotRuntimeClient().battery_voltage()

        state = _battery_state(
            voltage,
            low_voltage=(config_value.battery.low_voltage),
            critical_voltage=(config_value.battery.critical_voltage),
        )

        return BatteryStatus(
            available=True,
            voltage=voltage,
            state=state,
        )

    except (
        RobotRuntimeError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        return BatteryStatus(
            available=False,
            voltage=None,
            state="unknown",
            error=str(exc),
        )


def collect_robot_status(
    sensors_config: SensorsConfig,
) -> tuple[
    bool,
    BatteryStatus,
    SensorStatus,
    str | None,
]:
    """
    Collect live battery, grayscale, and ultrasonic
    status through the centralized robot runtime.
    """

    config_value = _validate_sensors_config(sensors_config)

    ultrasonic_configured = True

    client = RobotRuntimeClient()

    battery = collect_battery_status(config_value)

    grayscale_available = False
    grayscale_values: tuple[int, ...] | None = None
    grayscale_plausible: bool | None = None
    grayscale_suspicious_channels: tuple[int, ...] = ()
    grayscale_error: str | None = None

    try:
        first_values = client.grayscale_values()

        (
            grayscale_plausible,
            grayscale_suspicious_channels,
        ) = _grayscale_plausibility(
            client,
            first_values,
        )

        grayscale_available = True
        grayscale_values = tuple(int(value) for value in first_values)

    except (
        RobotRuntimeError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        grayscale_error = str(exc)

    (
        ultrasonic_available,
        ultrasonic_distance,
        ultrasonic_error,
    ) = _ultrasonic_status(client)

    sensors = SensorStatus(
        grayscale_available=grayscale_available,
        grayscale_values=grayscale_values,
        grayscale_plausible=grayscale_plausible,
        grayscale_suspicious_channels=(grayscale_suspicious_channels),
        ultrasonic_configured=ultrasonic_configured,
        ultrasonic_available=ultrasonic_available,
        ultrasonic_distance=ultrasonic_distance,
        ultrasonic_error=ultrasonic_error,
        error=grayscale_error,
    )

    passive_hardware_available = battery.available and grayscale_available

    passive_hardware_error = None

    if not passive_hardware_available:
        passive_hardware_error = battery.error or grayscale_error

    return (
        passive_hardware_available,
        battery,
        sensors,
        passive_hardware_error,
    )
