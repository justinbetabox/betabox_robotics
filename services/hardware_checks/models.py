from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class I2CStatus:
    available: bool
    devices: tuple[str, ...]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "devices": list(self.devices),
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class BatteryStatus:
    available: bool
    voltage: float | None
    state: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SensorStatus:
    grayscale_available: bool
    grayscale_values: tuple[int, ...] | None
    ultrasonic_configured: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "grayscale_available": (self.grayscale_available),
            "grayscale_values": (
                None if self.grayscale_values is None else list(self.grayscale_values)
            ),
            "ultrasonic_configured": (self.ultrasonic_configured),
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class AudioStatus:
    available: bool
    device: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VisionStatus:
    service_available: bool
    running: bool
    camera_running: bool
    camera_has_frame: bool
    clients: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RobotHardwareStatus:
    i2c: I2CStatus
    passive_hardware_available: bool
    battery: BatteryStatus
    sensors: SensorStatus
    audio: AudioStatus
    vision: VisionStatus
    passive_hardware_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "i2c": self.i2c.to_dict(),
            "passive_hardware_available": (self.passive_hardware_available),
            "battery": self.battery.to_dict(),
            "sensors": self.sensors.to_dict(),
            "audio": self.audio.to_dict(),
            "vision": self.vision.to_dict(),
            "passive_hardware_error": (self.passive_hardware_error),
        }
