from __future__ import annotations

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


def _validate_sensors_config(
    value: object,
) -> SensorsConfig:
    if not isinstance(
        value,
        SensorsConfig,
    ):
        raise TypeError("sensors_config must be a SensorsConfig")

    return value


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
            close = getattr(
                battery_sensor,
                "close",
                None,
            )

            if callable(close):
                try:
                    close()
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

    ultrasonic_configured = config_value.ultrasonic is not None
    battery = collect_battery_status(config_value)
    grayscale_sensor = None

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
                ultrasonic_configured=(ultrasonic_configured),
                error=("passive sensors could not be constructed"),
            ),
            str(exc),
        )

    try:
        try:
            grayscale_values = grayscale_sensor.read()

            sensors = SensorStatus(
                grayscale_available=True,
                grayscale_values=tuple(int(value) for value in grayscale_values),
                ultrasonic_configured=(ultrasonic_configured),
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
                ultrasonic_configured=(ultrasonic_configured),
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
        if grayscale_sensor is not None:
            close = getattr(
                grayscale_sensor,
                "close",
                None,
            )

            if callable(close):
                try:
                    close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass
