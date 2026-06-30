import logging
import math
from typing import List, Optional, Union

from .board import PWM_CHANNELS, PWMChannel
from .exceptions import HardwareError
from .i2c import I2C


class PWMError(HardwareError):
    """Raised when a PWM operation fails."""


TIMER_STATE = [{"period": 1} for _ in range(7)]


class PWM:
    """
    Betabox PWM channel abstraction.

    This currently talks to the Robot HAT PWM controller over I2C.
    """

    REG_CHN = 0x20
    REG_PSC = 0x40
    REG_ARR = 0x44
    REG_PSC2 = 0x50
    REG_ARR2 = 0x54

    ADDRESSES = [0x14, 0x15, 0x16]
    CLOCK = 72_000_000.0

    def __init__(
        self,
        channel: Union[int, str, PWMChannel],
        address: Optional[Union[int, List[int]]] = None,
        bus: Optional[I2C] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        self.channel = self._resolve_channel(channel)
        self.timer_index = self._timer_index_for_channel(self.channel)

        self._i2c = bus or I2C(address=address or self.ADDRESSES)
        self._owns_i2c = bus is None

        self._frequency = 50
        self._prescaler: Optional[int] = None
        self._pulse_width = 0
        self._duty_cycle: Optional[float] = None

        self.set_frequency(50)

    def _resolve_channel(self, channel: Union[int, str, PWMChannel]) -> int:
        if isinstance(channel, PWMChannel):
            return channel.value

        if isinstance(channel, str):
            if channel not in PWM_CHANNELS:
                raise PWMError(
                    f'Unknown PWM channel "{channel}". Valid channels: {list(PWM_CHANNELS.keys())}'
                )
            return PWM_CHANNELS[channel]

        if isinstance(channel, int):
            if channel not in PWM_CHANNELS.values():
                raise PWMError(f"PWM channel must be in range 0-19, not {channel}")
            return channel

        raise PWMError("channel must be an int, string channel name, or PWMChannel")

    def _timer_index_for_channel(self, channel: int) -> int:
        if channel < 16:
            return channel // 4
        if channel in (16, 17):
            return 4
        if channel == 18:
            return 5
        if channel == 19:
            return 6

        raise PWMError(f"Invalid PWM channel: {channel}")

    def _write_register_16(self, register: int, value: int) -> None:
        value = int(value)
        high = value >> 8
        low = value & 0xFF
        self._bus().write([register, high, low])

    def _bus(self) -> I2C:
        if self._i2c is None:
            raise PWMError("PWM I2C bus is closed")
        return self._i2c

    def set_frequency(self, frequency: float) -> None:
        if frequency <= 0:
            raise PWMError("frequency must be greater than 0")

        self._frequency = float(frequency)

        start = int(math.sqrt(self.CLOCK / self._frequency)) - 5
        if start <= 0:
            start = 1

        candidates = []

        for prescaler in range(start, start + 10):
            period = int(self.CLOCK / self._frequency / prescaler)
            actual = self.CLOCK / prescaler / period
            error = abs(self._frequency - actual)
            candidates.append((error, prescaler, period))

        _, prescaler, period = min(candidates, key=lambda item: item[0])

        self.set_prescaler(prescaler)
        self.set_period(period)

    def get_frequency(self) -> float:
        return self._frequency

    def set_prescaler(self, prescaler: float) -> None:
        prescaler = round(prescaler)

        if prescaler <= 0:
            raise PWMError("prescaler must be greater than 0")

        self._prescaler = prescaler
        self._frequency = (
            self.CLOCK / self._prescaler / TIMER_STATE[self.timer_index]["period"]
        )

        if self.timer_index < 4:
            register = self.REG_PSC + self.timer_index
        else:
            register = self.REG_PSC2 + self.timer_index - 4

        self._write_register_16(register, self._prescaler - 1)

    def get_prescaler(self) -> Optional[int]:
        return self._prescaler

    def set_period(self, period: float) -> None:
        period = round(period)

        if period <= 0:
            raise PWMError("period must be greater than 0")

        TIMER_STATE[self.timer_index]["period"] = period

        if self._prescaler:
            self._frequency = self.CLOCK / self._prescaler / period

        if self.timer_index < 4:
            register = self.REG_ARR + self.timer_index
        else:
            register = self.REG_ARR2 + self.timer_index - 4

        self._write_register_16(register, period)

    def get_period(self) -> int:
        return TIMER_STATE[self.timer_index]["period"]

    def set_pulse_width(self, pulse_width: float) -> None:
        pulse_width = int(pulse_width)

        if pulse_width < 0:
            raise PWMError("pulse_width must be greater than or equal to 0")

        period = self.get_period()

        if pulse_width > period:
            raise PWMError(f"pulse_width cannot be greater than period ({period})")

        self._pulse_width = pulse_width
        self._duty_cycle = pulse_width / period * 100

        register = self.REG_CHN + self.channel
        self._write_register_16(register, self._pulse_width)

    def get_pulse_width(self) -> int:
        return self._pulse_width

    def set_duty_cycle(self, percent: float) -> None:
        if percent < 0 or percent > 100:
            raise PWMError("duty cycle must be between 0 and 100")

        self._duty_cycle = float(percent)
        pulse_width = self._duty_cycle / 100.0 * self.get_period()
        self.set_pulse_width(pulse_width)

    def get_duty_cycle(self) -> Optional[float]:
        return self._duty_cycle

    def off(self) -> None:
        self.set_duty_cycle(0)

    # Compatibility aliases

    def freq(self, frequency: Optional[float] = None):
        if frequency is None:
            return self.get_frequency()
        self.set_frequency(frequency)

    def prescaler(self, prescaler: Optional[float] = None):
        if prescaler is None:
            return self.get_prescaler()
        self.set_prescaler(prescaler)

    def period(self, period: Optional[float] = None):
        if period is None:
            return self.get_period()
        self.set_period(period)

    def pulse_width(self, pulse_width: Optional[float] = None):
        if pulse_width is None:
            return self.get_pulse_width()
        self.set_pulse_width(pulse_width)

    def pulse_width_percent(self, percent: Optional[float] = None):
        if percent is None:
            return self.get_duty_cycle()
        self.set_duty_cycle(percent)

    def close(self) -> None:
        if self._owns_i2c and self._i2c is not None:
            self._i2c.close()
        self._i2c = None

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
