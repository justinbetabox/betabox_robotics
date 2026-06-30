from typing import Optional

from betabox_car.hardware import ADC, HardwareError
from betabox_car.robots import ROBOT


class BatteryError(HardwareError):
    """Raised when a battery sensor operation fails."""


class Battery:
    """
    Battery voltage monitor.

    Reads battery voltage through an ADC channel.

    The Robot HAT battery circuit uses a voltage divider, so the measured
    ADC voltage is multiplied by the configured scale factor.
    """

    DEFAULT_SCALE = 3.0

    def __init__(
        self,
        adc: Optional[ADC] = None,
        *,
        scale: Optional[float] = None,
        low_voltage: Optional[float] = None,
        critical_voltage: Optional[float] = None,
    ) -> None:
        scale_value = ROBOT.battery.scale if scale is None else scale
        low_voltage_value = (
            ROBOT.battery.low_voltage if low_voltage is None else low_voltage
        )
        critical_voltage_value = (
            ROBOT.battery.critical_voltage
            if critical_voltage is None
            else critical_voltage
        )

        if scale_value <= 0:
            raise BatteryError("scale must be greater than 0")

        if low_voltage_value <= 0:
            raise BatteryError("low_voltage must be greater than 0")

        if critical_voltage_value <= 0:
            raise BatteryError("critical_voltage must be greater than 0")

        if critical_voltage_value > low_voltage_value:
            raise BatteryError(
                "critical_voltage must be less than or equal to low_voltage"
            )

        self.adc = adc or ADC(ROBOT.battery.channel)
        self.scale = float(scale_value)
        self.low_voltage = float(low_voltage_value)
        self.critical_voltage = float(critical_voltage_value)

    def voltage(self) -> float:
        """
        Return battery voltage in volts.
        """
        return round(self.adc.read_voltage() * self.scale, 2)

    def read(self) -> float:
        """
        Compatibility alias.
        """
        return self.voltage()

    def is_low(self) -> bool:
        return self.voltage() <= self.low_voltage

    def is_critical(self) -> bool:
        return self.voltage() <= self.critical_voltage

    def status(self) -> str:
        voltage = self.voltage()

        if voltage <= self.critical_voltage:
            return "critical"

        if voltage <= self.low_voltage:
            return "low"

        return "ok"

    def close(self) -> None:
        self.adc.close()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
