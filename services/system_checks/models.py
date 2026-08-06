from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TemperatureStatus:
    celsius: float | None
    state: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ThrottlingStatus:
    raw: str | None
    undervoltage_now: bool
    undervoltage_occurred: bool
    throttled_now: bool
    throttled_occurred: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryStatus:
    total_mb: int | None
    available_mb: int | None
    used_percent: float | None
    state: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiskStatus:
    path: str
    total_gb: float | None
    free_gb: float | None
    used_percent: float | None
    state: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NetworkInterfaceStatus:
    name: str
    available: bool
    connected: bool
    state: str
    connection: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SystemHealthStatus:
    temperature: TemperatureStatus
    throttling: ThrottlingStatus
    memory: MemoryStatus
    disk: DiskStatus
    ethernet: NetworkInterfaceStatus
    wifi: NetworkInterfaceStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature.to_dict(),
            "throttling": self.throttling.to_dict(),
            "memory": self.memory.to_dict(),
            "disk": self.disk.to_dict(),
            "ethernet": self.ethernet.to_dict(),
            "wifi": self.wifi.to_dict(),
        }
