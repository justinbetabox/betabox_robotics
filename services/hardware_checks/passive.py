from __future__ import annotations

from typing import Final

from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots.config import SensorsConfig
from betabox_robotics.sensors import (
    Battery,
    BatteryError,
    Grayscale,
)

from .models import (
    BatteryStatus,
    SensorStatus,
)

GRAYSCALE_IMPLAUSIBLE_HIGH: Final[int] = 3000
GRAYSCALE_PLAUSIBILITY_SAMPLES: Final[int] = 5


def _validate_sensors_config(
    value: object,
) -> SensorsConfig:
    if not isinstance(
        value,
        SensorsConfig,
    ):
        raise TypeError("sensors_config must be a SensorsConfig")

    return value


def _grayscale_plausibility(
    sensor: Grayscale,
    first_values: list[int],
) -> tuple[bool, tuple[int, ...]]:
    samples = [first_values]

    for _ in range(GRAYSCALE_PLAUSIBILITY_SAMPLES - 1):
        samples.append(sensor.read())

    suspicious_channels = tuple(
        channel
        for channel in range(Grayscale.CHANNEL_COUNT)
        if all(sample[channel] > GRAYSCALE_IMPLAUSIBLE_HIGH for sample in samples)
    )

    return (
        not suspicious_channels,
        suspicious_channels,
    )


def collect_battery_status(
    sensors_config: SensorsConfig,
) -> BatteryStatus:
    """
    Collect the passive battery-sensor status.
    """

    config_value = _validate_sensors_config(sensors_config)
    battery_sensor = None

    try:
        battery_sensor = Battery.default(config_value.battery)

        voltage = float(battery_sensor.voltage())
        state = battery_sensor.status().value

        return BatteryStatus(
            available=True,
            voltage=voltage,
            state=state,
        )

    except (
        BatteryError,
        HardwareError,
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

    finally:
        if battery_sensor is not None:
            try:
                battery_sensor.close()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass


def collect_robot_status(
    sensors_config: SensorsConfig,
) -> tuple[
    bool,
    BatteryStatus,
    SensorStatus,
    str | None,
]:
    """
    Collect passive battery and grayscale sensor status.
    """

    config_value = _validate_sensors_config(sensors_config)

    ultrasonic_configured = True
    battery = collect_battery_status(config_value)

    try:
        grayscale_sensor = Grayscale.default(config_value.grayscale)
    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        return (
            False,
            battery,
            SensorStatus(
                grayscale_available=False,
                grayscale_values=None,
                grayscale_plausible=None,
                grayscale_suspicious_channels=(),
                ultrasonic_configured=ultrasonic_configured,
                error="passive sensors could not be constructed",
            ),
            str(exc),
        )

    try:
        try:
            grayscale_values = grayscale_sensor.read()

            (
                grayscale_plausible,
                grayscale_suspicious_channels,
            ) = _grayscale_plausibility(
                grayscale_sensor,
                grayscale_values,
            )

            sensors = SensorStatus(
                grayscale_available=True,
                grayscale_values=tuple(int(value) for value in grayscale_values),
                grayscale_plausible=grayscale_plausible,
                grayscale_suspicious_channels=grayscale_suspicious_channels,
                ultrasonic_configured=ultrasonic_configured,
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            sensors = SensorStatus(
                grayscale_available=False,
                grayscale_values=None,
                grayscale_plausible=None,
                grayscale_suspicious_channels=(),
                ultrasonic_configured=ultrasonic_configured,
                error=str(exc),
            )

        passive_hardware_available = battery.available and sensors.grayscale_available

        passive_hardware_error = None

        if not passive_hardware_available:
            passive_hardware_error = battery.error or sensors.error

        return (
            passive_hardware_available,
            battery,
            sensors,
            passive_hardware_error,
        )

    finally:
        try:
            grayscale_sensor.close()
        except (
            HardwareError,
            OSError,
            RuntimeError,
        ):
            pass
