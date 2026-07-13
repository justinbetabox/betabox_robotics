from __future__ import annotations

from typing import TYPE_CHECKING, Self

from betabox_robotics.hardware import ADC

from .exceptions import BatteryError
from .types import BatteryReading, BatteryState

if TYPE_CHECKING:
    from betabox_robotics.robots.config import BatteryConfig

class Battery:
    """
    Battery voltage monitor.

    Reads battery voltage through an ADC channel.

    The Robot HAT battery circuit uses a voltage divider, so the measured
    ADC voltage is multiplied by the configured scale factor.
    """

    DEFAULT_SCALE = 3.0
    DEFAULT_LOW_VOLTAGE = 6.6
    DEFAULT_CRITICAL_VOLTAGE = 6.2

    def __init__(
        self,
        adc: ADC,
        *,
        scale: float = DEFAULT_SCALE,
        low_voltage: float = DEFAULT_LOW_VOLTAGE,
        critical_voltage: float = DEFAULT_CRITICAL_VOLTAGE,
    ) -> None:
        if scale <= 0:
            raise BatteryError("scale must be greater than 0")

        if critical_voltage <= 0:
            raise BatteryError(
                "critical_voltage must be greater than 0"
            )

        if low_voltage <= critical_voltage:
            raise BatteryError(
                "low_voltage must be greater than critical_voltage"
            )

        self.adc = adc
        self.scale = float(scale)
        self.low_voltage = float(low_voltage)
        self.critical_voltage = float(critical_voltage)
        self._closed = False

    @classmethod
    def default(cls, config: "BatteryConfig") -> "Battery":
        return cls(
            ADC(config.channel),
            scale=config.scale,
            low_voltage=config.low_voltage,
            critical_voltage=config.critical_voltage,
        )

    @property
    def closed(self) -> bool:
        return self._closed


    def _require_open(self) -> None:
        if self._closed:
            raise BatteryError("battery sensor is closed")

    def voltage(self) -> float:
        """Return battery voltage in volts."""
        self._require_open()

        try:
            return round(
                self.adc.read_voltage() * self.scale,
                2,
            )
        except Exception as exc:
            raise BatteryError(
                f"failed to read battery voltage: {exc}"
            ) from exc


    def read(self) -> float:
        """Compatibility alias for voltage()."""
        return self.voltage()


    def status(self) -> BatteryState:
        voltage = self.voltage()
        return self._state_for_voltage(voltage)


    def reading(self) -> BatteryReading:
        voltage = self.voltage()

        return BatteryReading(
            voltage=voltage,
            state=self._state_for_voltage(voltage),
        )


    def is_low(self) -> bool:
        return self.reading().low


    def is_critical(self) -> bool:
        return self.reading().critical


    def _state_for_voltage(
        self,
        voltage: float,
    ) -> BatteryState:
        if voltage <= self.critical_voltage:
            return BatteryState.CRITICAL

        if voltage <= self.low_voltage:
            return BatteryState.LOW

        return BatteryState.OK

    def close(self) -> None:
        if self._closed:
            return

        try:
            self.adc.close()
        finally:
            self._closed = True


    def __enter__(self) -> Self:
        self._require_open()
        return self

    def deinit(self) -> None:
        self.close()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
