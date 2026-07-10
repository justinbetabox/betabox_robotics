from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class BatteryState(str, Enum):
    OK = "ok"
    LOW = "low"
    CRITICAL = "critical"


@dataclass(frozen=True)
class BatteryReading:
    voltage: float
    state: BatteryState

    @property
    def low(self) -> bool:
        return self.state in (
            BatteryState.LOW,
            BatteryState.CRITICAL,
        )

    @property
    def critical(self) -> bool:
        return self.state is BatteryState.CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "voltage": self.voltage,
            "state": self.state.value,
            "low": self.low,
        }


@dataclass(frozen=True)
class GrayscaleReading:
    raw: tuple[int, int, int]
    status: tuple[int, int, int]
    normalized: tuple[float, float, float] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UltrasonicReading:
    distance_cm: float
    samples_requested: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
