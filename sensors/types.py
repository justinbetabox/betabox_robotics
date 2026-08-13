from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class BatteryReadingDict(TypedDict):
    voltage: float
    state: str
    low: bool
    critical: bool


class GrayscaleReadingDict(TypedDict):
    raw: tuple[int, int, int]
    status: tuple[int, int, int]
    normalized: tuple[float, float, float] | None


class UltrasonicReadingDict(TypedDict):
    distance_cm: float
    samples_requested: int


class BatteryState(str, Enum):
    OK = "ok"
    LOW = "low"
    CRITICAL = "critical"


@dataclass(
    frozen=True,
    slots=True,
)
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

    def to_dict(
        self,
    ) -> BatteryReadingDict:
        return {
            "voltage": self.voltage,
            "state": self.state.value,
            "low": self.low,
            "critical": self.critical,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class GrayscaleReading:
    raw: tuple[int, int, int]
    status: tuple[int, int, int]
    normalized: tuple[float, float, float] | None

    def to_dict(
        self,
    ) -> GrayscaleReadingDict:
        return {
            "raw": self.raw,
            "status": self.status,
            "normalized": self.normalized,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class UltrasonicReading:
    distance_cm: float
    samples_requested: int

    def to_dict(
        self,
    ) -> UltrasonicReadingDict:
        return {
            "distance_cm": self.distance_cm,
            "samples_requested": self.samples_requested,
        }
