from betabox_robotics.hardware import ADC, HardwareError


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
        self.adc = adc
        self.scale = scale
        self.low_voltage = low_voltage
        self.critical_voltage = critical_voltage

    @classmethod
    def default(
        cls,
        robot_config,
        *,
        scale: float | None = None,
        low_voltage: float | None = None,
        critical_voltage: float | None = None,
    ) -> "Battery":
        cfg = robot_config.battery

        return cls(
            ADC(cfg.channel),
            scale=cfg.scale if scale is None else scale,
            low_voltage=cfg.low_voltage if low_voltage is None else low_voltage,
            critical_voltage=(
                cfg.critical_voltage if critical_voltage is None else critical_voltage
            ),
        )

    def voltage(self) -> float:
        """
        Return battery voltage in volts.
        """
        return round(self.adc.read_voltage() * self.scale, 2)

    def read(self) -> float:
        """Compatibility alias."""
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

    def __enter__(self) -> "Battery":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
