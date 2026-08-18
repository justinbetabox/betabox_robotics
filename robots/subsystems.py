from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from betabox_robotics.camera import CameraMountStatus
from betabox_robotics.drive import DriveStatus
from betabox_robotics.sensors import (
    BatteryReading,
    BatteryState,
    GrayscaleReading,
    SensorsStatus,
    UltrasonicReading,
)


class DriveSubsystem(Protocol):
    """Drive operations required by a car-style robot."""

    def forward(
        self,
        speed: float,
    ) -> None: ...

    def backward(
        self,
        speed: float,
    ) -> None: ...

    def stop(
        self,
    ) -> None: ...

    def left(
        self,
        angle: float = 30,
    ) -> None: ...

    def right(
        self,
        angle: float = 30,
    ) -> None: ...

    def center(
        self,
    ) -> None: ...

    def status(
        self,
    ) -> DriveStatus: ...


class CameraMountSubsystem(Protocol):
    """Camera mount operations required by a car-style robot."""

    def look(
        self,
        *,
        pan: float | None = None,
        tilt: float | None = None,
        smooth: bool = True,
    ) -> None: ...

    def pan(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None: ...

    def tilt(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None: ...

    def center(
        self,
        *,
        smooth: bool = True,
    ) -> None: ...

    def status(
        self,
    ) -> CameraMountStatus: ...


class UltrasonicSubsystem(Protocol):
    """Ultrasonic operations required by a car-style robot."""

    def distance(
        self,
        samples: int = 10,
    ) -> float: ...

    def reading(
        self,
        samples: int = 10,
    ) -> UltrasonicReading: ...


class BatterySubsystem(Protocol):
    """Battery operations required by a car-style robot."""

    def voltage(
        self,
    ) -> float: ...

    def is_low(
        self,
    ) -> bool: ...

    def is_critical(
        self,
    ) -> bool: ...

    def status(
        self,
    ) -> BatteryState: ...

    def reading(
        self,
    ) -> BatteryReading: ...


class GrayscaleSubsystem(Protocol):
    """Grayscale operations required by a car-style robot."""

    def status(
        self,
        raw: Sequence[int | float] | None = None,
        threshold: float = 0.5,
    ) -> list[int]: ...

    def read(
        self,
    ) -> list[int]: ...

    def normalized(
        self,
        raw: Sequence[int | float] | None = None,
    ) -> list[float]: ...

    def reading(
        self,
        *,
        threshold: float = 0.5,
    ) -> GrayscaleReading: ...


class SensorsSubsystem(Protocol):
    """Sensor operations required by a car-style robot."""

    @property
    def ultrasonic(
        self,
    ) -> UltrasonicSubsystem: ...

    @property
    def grayscale(
        self,
    ) -> GrayscaleSubsystem: ...

    @property
    def battery(
        self,
    ) -> BatterySubsystem: ...

    def status(
        self,
    ) -> SensorsStatus: ...
