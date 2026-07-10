from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from betabox_robotics.vision import VisionClient, VisionClientError


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
    robot_available: bool
    battery: BatteryStatus
    sensors: SensorStatus
    audio: AudioStatus
    vision: VisionStatus
    robot_error: str | None = None

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

def collect_i2c_status() -> I2CStatus:
    device = Path("/dev/i2c-1")

    if not device.exists():
        return I2CStatus(
            available=False,
            devices=[],
            error="/dev/i2c-1 is missing",
        )

    result = run(["i2cdetect", "-y", "1"], timeout=5)

    if result is None:
        return I2CStatus(
            available=True,
            devices=[],
            error="could not run i2cdetect",
        )

    if result.returncode != 0:
        message = result.stderr.strip() or "i2cdetect failed"

        return I2CStatus(
            available=True,
            devices=[],
            error=message,
        )

    devices: list[str] = []

    for line in result.stdout.splitlines():
        if ":" not in line:
            continue

        _, values = line.split(":", maxsplit=1)

        for value in values.split():
            if value == "--":
                continue

            if len(value) == 2:
                try:
                    int(value, 16)
                except ValueError:
                    continue

                devices.append(f"0x{value.lower()}")

    return I2CStatus(
        available=True,
        devices=sorted(set(devices)),
    )

def collect_audio_status() -> AudioStatus:
    result = run(["aplay", "-l"], timeout=5)

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
            error=output.strip() or "aplay failed",
        )

    if "snd_rpi_hifiberry_dac" in output or "HifiBerry" in output:
        return AudioStatus(
            available=True,
            device="HifiBerry DAC",
        )

    return AudioStatus(
        available=False,
        device=None,
        error="HifiBerry audio device was not detected",
    )

def collect_vision_status() -> VisionStatus:
    client = VisionClient()

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

    camera = statistics.get("camera", {})
    streaming = statistics.get("streaming", {})

    return VisionStatus(
        service_available=True,
        running=bool(statistics.get("running", False)),
        camera_running=bool(camera.get("running", False)),
        camera_has_frame=bool(camera.get("has_frame", False)),
        clients=int(streaming.get("clients", 0)),
    )

def collect_robot_status() -> tuple[
    bool,
    BatteryStatus,
    SensorStatus,
    str | None,
]:
    try:
        from betabox_robotics.robots.betabox_car import BETABOX_CAR
        from betabox_robotics.sensors import Sensors

        sensors = Sensors.default(BETABOX_CAR)
    except Exception as exc:
        return (
            False,
            BatteryStatus(
                available=False,
                voltage=None,
                state="unknown",
                error="sensors could not be constructed",
            ),
            SensorStatus(
                grayscale_available=False,
                grayscale_values=None,
                ultrasonic_configured=False,
                error="sensors could not be constructed",
            ),
            str(exc),
        )

    try:
        try:
            voltage = float(sensors.battery.voltage())
            battery_state = str(sensors.battery.status())

            battery = BatteryStatus(
                available=True,
                voltage=voltage,
                state=battery_state,
            )
        except Exception as exc:
            battery = BatteryStatus(
                available=False,
                voltage=None,
                state="unknown",
                error=str(exc),
            )

        try:
            grayscale_values = sensors.grayscale.read()

            sensor_status = SensorStatus(
                grayscale_available=True,
                grayscale_values=grayscale_values,
                ultrasonic_configured=True,
            )
        except Exception as exc:
            sensor_status = SensorStatus(
                grayscale_available=False,
                grayscale_values=None,
                ultrasonic_configured=True,
                error=str(exc),
            )

        return True, battery, sensor_status, None

    finally:
        close = getattr(sensors, "close", None)

        if callable(close):
            try:
                close()
            except Exception:
                pass

def collect_hardware_status() -> RobotHardwareStatus:
    i2c = collect_i2c_status()
    audio = collect_audio_status()
    vision = collect_vision_status()

    (
        robot_available,
        battery,
        sensors,
        robot_error,
    ) = collect_robot_status()

    return RobotHardwareStatus(
        i2c=i2c,
        robot_available=robot_available,
        battery=battery,
        sensors=sensors,
        audio=audio,
        vision=vision,
        robot_error=robot_error,
    )

def main() -> int:
    import json

    status = collect_hardware_status()
    print(json.dumps(status.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
