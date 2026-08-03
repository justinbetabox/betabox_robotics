from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Self

from betabox_robotics.hardware import HardwareError

from .battery import Battery
from .exceptions import SensorsError
from .grayscale import Grayscale
from .ultrasonic import Ultrasonic

if TYPE_CHECKING:
    from betabox_robotics.robots.config import SensorsConfig


@dataclass(
    frozen=True,
    slots=True,
)
class SensorsStatus:
    ultrasonic_closed: bool
    grayscale_closed: bool
    battery_closed: bool
    closed: bool

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


class Sensors:
    """
    Combined Betabox sensor subsystem.

    The subsystem owns its Ultrasonic, Grayscale, and Battery components
    and closes them when the subsystem is closed.
    """

    def __init__(
        self,
        *,
        ultrasonic: Ultrasonic,
        grayscale: Grayscale,
        battery: Battery,
    ) -> None:
        if not isinstance(
            ultrasonic,
            Ultrasonic,
        ):
            raise TypeError("ultrasonic must be an Ultrasonic instance")

        if not isinstance(
            grayscale,
            Grayscale,
        ):
            raise TypeError("grayscale must be a Grayscale instance")

        if not isinstance(
            battery,
            Battery,
        ):
            raise TypeError("battery must be a Battery instance")

        self.ultrasonic = ultrasonic
        self.grayscale = grayscale
        self.battery = battery
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise SensorsError("sensors subsystem is closed")

    def status(self) -> SensorsStatus:
        return SensorsStatus(
            ultrasonic_closed=self.ultrasonic.closed,
            grayscale_closed=self.grayscale.closed,
            battery_closed=self.battery.closed,
            closed=self.closed,
        )

    @classmethod
    def default(
        cls,
        config: SensorsConfig,
    ) -> Self:
        ultrasonic: Ultrasonic | None = None
        grayscale: Grayscale | None = None
        battery: Battery | None = None

        try:
            ultrasonic = Ultrasonic.default(config.ultrasonic)

            grayscale = Grayscale.default(config.grayscale)

            battery = Battery.default(config.battery)

            return cls(
                ultrasonic=ultrasonic,
                grayscale=grayscale,
                battery=battery,
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            # Close in reverse construction order.
            for component in (
                battery,
                grayscale,
                ultrasonic,
            ):
                if component is None:
                    continue

                try:
                    component.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            raise

    def close(self) -> None:
        if self._closed:
            return

        first_error: HardwareError | OSError | RuntimeError | None = None

        try:
            # Close in reverse construction order.
            for component in (
                self.battery,
                self.grayscale,
                self.ultrasonic,
            ):
                try:
                    component.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ) as exc:
                    if first_error is None:
                        first_error = exc

        finally:
            self._closed = True

        if first_error is not None:
            raise first_error

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
