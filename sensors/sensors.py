from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Self

from .battery import Battery
from .grayscale import Grayscale
from .ultrasonic import Ultrasonic

from .exceptions import SensorsError


@dataclass(frozen=True)
class SensorsStatus:
    ultrasonic_closed: bool
    grayscale_closed: bool
    battery_closed: bool
    closed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Sensors:
    """
    Sensor subsystem.
    """

    def __init__(
        self,
        *,
        ultrasonic: Ultrasonic,
        grayscale: Grayscale,
        battery: Battery,
    ) -> None:
        self.ultrasonic = ultrasonic
        self.grayscale = grayscale
        self.battery = battery
        self._closed = False


    @property
    def closed(self) -> bool:
        return self._closed


    def status(self) -> SensorsStatus:
        return SensorsStatus(
            ultrasonic_closed=self.ultrasonic.closed,
            grayscale_closed=self.grayscale.closed,
            battery_closed=self.battery.closed,
            closed=self.closed,
        )

    @classmethod
    def default(cls, robot_config) -> "Sensors":
        return cls(
            ultrasonic=Ultrasonic.default(robot_config),
            grayscale=Grayscale.default(robot_config),
            battery=Battery.default(robot_config),
        )

    def close(self) -> None:
        if self._closed:
            return

        try:
            self.ultrasonic.close()
        finally:
            try:
                self.grayscale.close()
            finally:
                try:
                    self.battery.close()
                finally:
                    self._closed = True

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        if self._closed:
            raise SensorsError("sensors subsystem is closed")

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
