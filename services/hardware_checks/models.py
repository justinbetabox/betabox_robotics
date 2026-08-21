from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class I2CStatusData(TypedDict):
    available: bool
    devices: list[str]
    error: str | None


class BatteryStatusData(TypedDict):
    available: bool
    voltage: float | None
    state: str
    error: str | None


class SensorStatusData(TypedDict):
    grayscale_available: bool
    grayscale_values: list[int] | None
    grayscale_plausible: bool | None
    grayscale_suspicious_channels: list[int]
    ultrasonic_configured: bool
    ultrasonic_available: bool
    ultrasonic_distance: float | None
    ultrasonic_error: str | None
    error: str | None


class AudioStatusData(TypedDict):
    available: bool
    device: str | None
    error: str | None


class VisionStatusData(TypedDict):
    service_available: bool
    running: bool
    camera_running: bool
    camera_has_frame: bool
    clients: int
    error: str | None


class RobotHardwareStatusData(TypedDict):
    i2c: I2CStatusData
    passive_hardware_available: bool
    battery: BatteryStatusData
    sensors: SensorStatusData
    audio: AudioStatusData
    vision: VisionStatusData
    passive_hardware_error: str | None


@dataclass(frozen=True, slots=True)
class I2CStatus:
    available: bool
    devices: tuple[str, ...]
    error: str | None = None

    def to_dict(
        self,
    ) -> I2CStatusData:
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

    def to_dict(
        self,
    ) -> BatteryStatusData:
        return {
            "available": self.available,
            "voltage": self.voltage,
            "state": self.state,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class SensorStatus:
    grayscale_available: bool
    grayscale_values: tuple[int, ...] | None
    grayscale_plausible: bool | None
    grayscale_suspicious_channels: tuple[int, ...]
    ultrasonic_configured: bool
    ultrasonic_available: bool
    ultrasonic_distance: float | None
    ultrasonic_error: str | None = None
    error: str | None = None

    def to_dict(
        self,
    ) -> SensorStatusData:
        return {
            "grayscale_available": self.grayscale_available,
            "grayscale_values": (
                None if self.grayscale_values is None else list(self.grayscale_values)
            ),
            "grayscale_plausible": self.grayscale_plausible,
            "grayscale_suspicious_channels": list(self.grayscale_suspicious_channels),
            "ultrasonic_configured": self.ultrasonic_configured,
            "ultrasonic_available": self.ultrasonic_available,
            "ultrasonic_distance": self.ultrasonic_distance,
            "ultrasonic_error": self.ultrasonic_error,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class AudioStatus:
    available: bool
    device: str | None
    error: str | None = None

    def to_dict(
        self,
    ) -> AudioStatusData:
        return {
            "available": self.available,
            "device": self.device,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class VisionStatus:
    service_available: bool
    running: bool
    camera_running: bool
    camera_has_frame: bool
    clients: int
    error: str | None = None

    def to_dict(
        self,
    ) -> VisionStatusData:
        return {
            "service_available": self.service_available,
            "running": self.running,
            "camera_running": self.camera_running,
            "camera_has_frame": self.camera_has_frame,
            "clients": self.clients,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class RobotHardwareStatus:
    i2c: I2CStatus
    passive_hardware_available: bool
    battery: BatteryStatus
    sensors: SensorStatus
    audio: AudioStatus
    vision: VisionStatus
    passive_hardware_error: str | None = None

    def to_dict(
        self,
    ) -> RobotHardwareStatusData:
        return {
            "i2c": self.i2c.to_dict(),
            "passive_hardware_available": self.passive_hardware_available,
            "battery": self.battery.to_dict(),
            "sensors": self.sensors.to_dict(),
            "audio": self.audio.to_dict(),
            "vision": self.vision.to_dict(),
            "passive_hardware_error": self.passive_hardware_error,
        }
