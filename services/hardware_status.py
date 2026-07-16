from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.vision import (
    VisionClient,
    VisionClientError,
)


@dataclass(frozen=True)
class I2CStatus:
    available: bool
    devices: list[str]
    error: str | None = None


@dataclass(frozen=True)
class BatteryStatus:
    available: bool
    voltage: float | None
    state: str
    error: str | None = None


@dataclass(frozen=True)
class SensorStatus:
    grayscale_available: bool
    grayscale_values: list[int] | None
    ultrasonic_configured: bool
    error: str | None = None


@dataclass(frozen=True)
class AudioStatus:
    available: bool
    device: str | None
    error: str | None = None


@dataclass(frozen=True)
class VisionStatus:
    service_available: bool
    running: bool
    camera_running: bool
    camera_has_frame: bool
    clients: int
    error: str | None = None


@dataclass(frozen=True)
class RobotHardwareStatus:
    i2c: I2CStatus
    passive_hardware_available: bool
    battery: BatteryStatus
    sensors: SensorStatus
    audio: AudioStatus
    vision: VisionStatus
    passive_hardware_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run(
    command: list[str],
    *,
    timeout: int = 5,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None


def collect_i2c_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> I2CStatus:
    device = config.verification.i2c_device

    if not device.exists():
        return I2CStatus(
            available=False,
            devices=[],
            error=f"{device} is missing",
        )

    result = run(
        [
            "i2cdetect",
            "-y",
            str(config.verification.i2c_bus),
        ],
        timeout=config.verification.command_timeout_seconds,
    )

    if result is None:
        return I2CStatus(
            available=True,
            devices=[],
            error="could not run i2cdetect",
        )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or "i2cdetect failed"
        )

        return I2CStatus(
            available=True,
            devices=[],
            error=message,
        )

    devices: list[str] = []

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
                int(value, 16)
            except ValueError:
                continue

            devices.append(
                f"0x{value.lower()}"
            )

    return I2CStatus(
        available=True,
        devices=sorted(set(devices)),
    )


def collect_audio_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> AudioStatus:
    result = run(
        ["aplay", "-l"],
        timeout=config.verification.command_timeout_seconds,
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
            error=(
                output.strip()
                or "aplay failed"
            ),
        )

    detected = any(
        identifier in output
        for identifier in (
            config.verification.hifiberry_identifiers
        )
    )

    if detected:
        return AudioStatus(
            available=True,
            device="HifiBerry DAC",
        )

    return AudioStatus(
        available=False,
        device=None,
        error=(
            "HifiBerry audio device "
            "was not detected"
        ),
    )


def collect_vision_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> VisionStatus:
    client = VisionClient(
        base_url=config.network.vision_url,
        timeout=float(
            config.verification.command_timeout_seconds
        ),
    )

    try:
        statistics = client.statistics()
    except VisionClientError as exc:
        return VisionStatus(
            service_available=False,
            running=False,
            camera_running=False,
            camera_has_frame=False,
            clients=0,
            error=str(exc),
        )

    return VisionStatus(
        service_available=True,
        running=statistics.running,
        camera_running=statistics.camera.running,
        camera_has_frame=(
            statistics.camera.has_frame
        ),
        clients=statistics.streaming.clients,
    )


def collect_robot_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[
    bool,
    BatteryStatus,
    SensorStatus,
    str | None,
]:
    grayscale_sensor = None
    ultrasonic_configured = False

    battery = collect_battery_status(
        config
    )

    try:
        from betabox_robotics.robots.betabox_car import (
            BETABOX_CAR,
        )
        from betabox_robotics.sensors import (
            Grayscale,
        )

        ultrasonic_configured = (
            BETABOX_CAR.sensors.ultrasonic
            is not None
        )

        grayscale_sensor = Grayscale.default(
            BETABOX_CAR.sensors.grayscale
        )

    except Exception as exc:
        return (
            False,
            battery,
            SensorStatus(
                grayscale_available=False,
                grayscale_values=None,
                ultrasonic_configured=(
                    ultrasonic_configured
                ),
                error=(
                    "passive sensors could "
                    "not be constructed"
                ),
            ),
            str(exc),
        )

    try:
        try:
            grayscale_values = (
                grayscale_sensor.read()
            )

            sensors = SensorStatus(
                grayscale_available=True,
                grayscale_values=(
                    grayscale_values
                ),
                ultrasonic_configured=(
                    ultrasonic_configured
                ),
            )

        except Exception as exc:
            sensors = SensorStatus(
                grayscale_available=False,
                grayscale_values=None,
                ultrasonic_configured=(
                    ultrasonic_configured
                ),
                error=str(exc),
            )

        passive_hardware_available = (
            battery.available
            and sensors.grayscale_available
        )

        passive_hardware_error = None

        if not passive_hardware_available:
            passive_hardware_error = (
                battery.error
                or sensors.error
            )

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
                except Exception:
                    pass


def collect_battery_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> BatteryStatus:
    battery_sensor = None

    try:
        from betabox_robotics.robots.betabox_car import (
            BETABOX_CAR,
        )
        from betabox_robotics.sensors import Battery

        battery_sensor = Battery.default(
            BETABOX_CAR.sensors.battery
        )

        voltage = float(
            battery_sensor.voltage()
        )

        state = (
            battery_sensor.status().value
        )

        return BatteryStatus(
            available=True,
            voltage=voltage,
            state=state,
        )

    except Exception as exc:
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
                except Exception:
                    pass


def collect_hardware_status(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> RobotHardwareStatus:
    i2c = collect_i2c_status(config)
    audio = collect_audio_status(config)
    vision = collect_vision_status(config)

    (
        passive_hardware_available,
        battery,
        sensors,
        passive_hardware_error,
    ) = collect_robot_status(config)

    return RobotHardwareStatus(
        i2c=i2c,
        passive_hardware_available=passive_hardware_available,
        battery=battery,
        sensors=sensors,
        audio=audio,
        vision=vision,
        passive_hardware_error=passive_hardware_error,
    )


def main() -> int:
    import json

    config = DEFAULT_PLATFORM_CONFIG
    status = collect_hardware_status(config)

    print(
        json.dumps(
            status.to_dict(),
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
