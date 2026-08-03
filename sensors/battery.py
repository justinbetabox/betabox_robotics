from __future__ import annotations

import math
from typing import TYPE_CHECKING, ClassVar, Self

from betabox_robotics.hardware import (
    ADC,
    HardwareError,
)

from .exceptions import BatteryError
from .types import (
    BatteryReading,
    BatteryState,
)

if TYPE_CHECKING:
    from betabox_robotics.robots.config import (
        BatteryConfig,
    )


class Battery:
    """
    Battery voltage monitor.

    Reads battery voltage through an ADC channel.

    The Robot HAT battery circuit uses a voltage divider, so the measured
    ADC voltage is multiplied by the configured scale factor.

    The Battery owns the supplied ADC object and closes it when the
    battery sensor is closed.
    """

    DEFAULT_SCALE: ClassVar[float] = 3.0
    DEFAULT_LOW_VOLTAGE: ClassVar[float] = 6.6
    DEFAULT_CRITICAL_VOLTAGE: ClassVar[float] = 6.2

    def __init__(
        self,
        adc: ADC,
        *,
        scale: float = DEFAULT_SCALE,
        low_voltage: float = DEFAULT_LOW_VOLTAGE,
        critical_voltage: float = DEFAULT_CRITICAL_VOLTAGE,
    ) -> None:
        if not isinstance(
            adc,
            ADC,
        ):
            raise TypeError("adc must be an ADC instance")

        scale_value = self._require_finite_number(
            scale,
            name="scale",
        )

        low_voltage_value = self._require_finite_number(
            low_voltage,
            name="low_voltage",
        )

        critical_voltage_value = self._require_finite_number(
            critical_voltage,
            name="critical_voltage",
        )

        if scale_value <= 0:
            raise BatteryError("scale must be greater than 0")

        if critical_voltage_value <= 0:
            raise BatteryError("critical_voltage must be greater than 0")

        if low_voltage_value <= critical_voltage_value:
            raise BatteryError("low_voltage must be greater than critical_voltage")

        self.adc = adc
        self.scale = scale_value
        self.low_voltage = low_voltage_value
        self.critical_voltage = critical_voltage_value
        self._closed = False

    @staticmethod
    def _require_finite_number(
        value: object,
        *,
        name: str,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            int | float,
        ):
            raise TypeError(f"{name} must be a number")

        result = float(value)

        if not math.isfinite(result):
            raise ValueError(f"{name} must be finite")

        return result

    @classmethod
    def default(
        cls,
        config: BatteryConfig,
    ) -> Self:
        adc: ADC | None = None

        try:
            adc = ADC(config.channel)

            return cls(
                adc,
                scale=config.scale,
                low_voltage=config.low_voltage,
                critical_voltage=config.critical_voltage,
            )

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            if adc is not None:
                try:
                    adc.close()
                except (
                    HardwareError,
                    OSError,
                    RuntimeError,
                ):
                    pass

            raise

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise BatteryError("battery sensor is closed")

    def voltage(self) -> float:
        """Return the scaled battery voltage in volts."""

        self._require_open()

        try:
            measured_voltage = self.adc.read_voltage()

            measured_value = self._require_finite_number(
                measured_voltage,
                name="ADC voltage",
            )

            if measured_value < 0:
                raise BatteryError("ADC voltage cannot be negative")

            battery_voltage = measured_value * self.scale

            if not math.isfinite(battery_voltage):
                raise BatteryError("calculated battery voltage is not finite")

            return round(
                battery_voltage,
                2,
            )

        except BatteryError:
            raise

        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise BatteryError(f"failed to read battery voltage: {exc}") from exc

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
