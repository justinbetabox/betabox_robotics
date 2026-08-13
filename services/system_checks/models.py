from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class TemperatureStatusData(TypedDict):
    celsius: float | None
    state: str
    error: str | None


class ThrottlingStatusData(TypedDict):
    raw: str | None
    undervoltage_now: bool
    undervoltage_occurred: bool
    throttled_now: bool
    throttled_occurred: bool
    error: str | None


class MemoryStatusData(TypedDict):
    total_mb: int | None
    available_mb: int | None
    used_percent: float | None
    state: str
    error: str | None


class DiskStatusData(TypedDict):
    path: str
    total_gb: float | None
    free_gb: float | None
    used_percent: float | None
    state: str
    error: str | None


class NetworkInterfaceStatusData(TypedDict):
    name: str
    available: bool
    connected: bool
    state: str
    connection: str | None
    error: str | None


class SystemHealthStatusData(TypedDict):
    temperature: TemperatureStatusData
    throttling: ThrottlingStatusData
    memory: MemoryStatusData
    disk: DiskStatusData
    ethernet: NetworkInterfaceStatusData
    wifi: NetworkInterfaceStatusData


@dataclass(frozen=True, slots=True)
class TemperatureStatus:
    celsius: float | None
    state: str
    error: str | None = None

    def to_dict(self) -> TemperatureStatusData:
        return {
            "celsius": self.celsius,
            "state": self.state,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class ThrottlingStatus:
    raw: str | None
    undervoltage_now: bool
    undervoltage_occurred: bool
    throttled_now: bool
    throttled_occurred: bool
    error: str | None = None

    def to_dict(self) -> ThrottlingStatusData:
        return {
            "raw": self.raw,
            "undervoltage_now": self.undervoltage_now,
            "undervoltage_occurred": self.undervoltage_occurred,
            "throttled_now": self.throttled_now,
            "throttled_occurred": self.throttled_occurred,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class MemoryStatus:
    total_mb: int | None
    available_mb: int | None
    used_percent: float | None
    state: str
    error: str | None = None

    def to_dict(self) -> MemoryStatusData:
        return {
            "total_mb": self.total_mb,
            "available_mb": self.available_mb,
            "used_percent": self.used_percent,
            "state": self.state,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class DiskStatus:
    path: str
    total_gb: float | None
    free_gb: float | None
    used_percent: float | None
    state: str
    error: str | None = None

    def to_dict(self) -> DiskStatusData:
        return {
            "path": self.path,
            "total_gb": self.total_gb,
            "free_gb": self.free_gb,
            "used_percent": self.used_percent,
            "state": self.state,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class NetworkInterfaceStatus:
    name: str
    available: bool
    connected: bool
    state: str
    connection: str | None
    error: str | None = None

    def to_dict(self) -> NetworkInterfaceStatusData:
        return {
            "name": self.name,
            "available": self.available,
            "connected": self.connected,
            "state": self.state,
            "connection": self.connection,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class SystemHealthStatus:
    temperature: TemperatureStatus
    throttling: ThrottlingStatus
    memory: MemoryStatus
    disk: DiskStatus
    ethernet: NetworkInterfaceStatus
    wifi: NetworkInterfaceStatus

    def to_dict(self) -> SystemHealthStatusData:
        return {
            "temperature": self.temperature.to_dict(),
            "throttling": self.throttling.to_dict(),
            "memory": self.memory.to_dict(),
            "disk": self.disk.to_dict(),
            "ethernet": self.ethernet.to_dict(),
            "wifi": self.wifi.to_dict(),
        }
