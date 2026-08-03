from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from typing import ClassVar, Self, TypedDict

from .board import PWM_CHANNELS, PWMChannel
from .exceptions import HardwareError
from .i2c import I2C


class PWMError(HardwareError):
    """Raised when a PWM operation fails."""


class TimerState(TypedDict):
    period: int


TIMER_STATE: list[TimerState] = [
    {
        "period": 1,
    }
    for _ in range(7)
]


class PWM:
    """
    Betabox PWM channel abstraction.

    This currently talks to the Robot HAT PWM controller over I²C.
    A PWM created without an injected I²C bus owns and closes that bus.
    An injected bus is borrowed and remains owned by the caller.
    """

    REG_CHN: ClassVar[int] = 0x20
    REG_PSC: ClassVar[int] = 0x40
    REG_ARR: ClassVar[int] = 0x44
    REG_PSC2: ClassVar[int] = 0x50
    REG_ARR2: ClassVar[int] = 0x54

    CLOCK: ClassVar[float] = 72_000_000.0
    DEFAULT_FREQUENCY: ClassVar[float] = 50.0

    ADDRESSES: ClassVar[tuple[int, ...]] = (
        0x14,
        0x15,
        0x16,
    )

    def __init__(
        self,
        channel: int | str | PWMChannel,
        address: int | Sequence[int] | None = None,
        bus: I2C | None = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        self.channel = self._resolve_channel(channel)

        self.timer_index = self._timer_index_for_channel(self.channel)

        self._i2c: I2C | None = None
        self._owns_i2c = bus is None

        self._frequency = self.DEFAULT_FREQUENCY
        self._prescaler: int | None = None
        self._pulse_width = 0
        self._duty_cycle: float | None = None

        try:
            self._i2c = (
                bus
                if bus is not None
                else I2C(address=(self.ADDRESSES if address is None else address))
            )

            self.set_frequency(self.DEFAULT_FREQUENCY)

        except BaseException:
            self.close()
            raise

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

    def _resolve_channel(
        self,
        channel: int | str | PWMChannel,
    ) -> int:
        if isinstance(channel, PWMChannel):
            return int(channel)

        if isinstance(channel, str):
            try:
                return PWM_CHANNELS[channel]
            except KeyError:
                valid_channels = ", ".join(PWM_CHANNELS)

                raise PWMError(
                    f'Unknown PWM channel "{channel}". Valid channels: {valid_channels}'
                ) from None

        if isinstance(channel, bool):
            raise TypeError(
                "channel must be an int, string channel name, or PWMChannel"
            )

        if isinstance(channel, int):
            if channel not in PWM_CHANNELS.values():
                raise PWMError(f"PWM channel must be in range 0-19, not {channel}")

            return channel

        raise TypeError("channel must be an int, string channel name, or PWMChannel")

    @staticmethod
    def _timer_index_for_channel(
        channel: int,
    ) -> int:
        if 0 <= channel < 16:
            return channel // 4

        if channel in (
            16,
            17,
        ):
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

    @property
    def closed(self) -> bool:
        return self._i2c is None

    def _bus(self) -> I2C:
        bus = self._i2c

        if bus is None:
            raise PWMError("PWM I2C bus is closed")

        return bus

    def set_frequency(
        self,
        frequency: float,
    ) -> None:
        value = self._require_finite_number(
            frequency,
            name="frequency",
        )

        if value <= 0:
            raise PWMError("frequency must be greater than 0")

        start = max(
            1,
            int(math.sqrt(self.CLOCK / value)) - 5,
        )

        candidates: list[tuple[float, int, int]] = []

        for prescaler in range(
            start,
            start + 10,
        ):
            period = int(self.CLOCK / value / prescaler)

            if period <= 0:
                continue

            actual = self.CLOCK / prescaler / period

            candidates.append(
                (
                    abs(value - actual),
                    prescaler,
                    period,
                )
            )

        if not candidates:
            raise PWMError("frequency cannot be represented")

        _, prescaler, period = min(
            candidates,
            key=lambda item: item[0],
        )

        self.set_prescaler(prescaler)
        self.set_period(period)

    def get_frequency(self) -> float:
        return self._frequency

    def set_prescaler(
        self,
        prescaler: float,
    ) -> None:
        value = self._require_finite_number(
            prescaler,
            name="prescaler",
        )

        rounded = round(value)

        if rounded <= 0:
            raise PWMError("prescaler must be greater than 0")

        self._prescaler = rounded

        self._frequency = self.CLOCK / rounded / self.get_period()

        if self.timer_index < 4:
            register = self.REG_PSC + self.timer_index
        else:
            register = self.REG_PSC2 + self.timer_index - 4

        self._write_register_16(
            register,
            rounded - 1,
        )

    def get_prescaler(
        self,
    ) -> int | None:
        return self._prescaler

    def set_period(
        self,
        period: float,
    ) -> None:
        value = self._require_finite_number(
            period,
            name="period",
        )

        rounded = round(value)

        if rounded <= 0:
            raise PWMError("period must be greater than 0")

        TIMER_STATE[self.timer_index]["period"] = rounded

        if self._prescaler is not None:
            self._frequency = self.CLOCK / self._prescaler / rounded

        if self.timer_index < 4:
            register = self.REG_ARR + self.timer_index
        else:
            register = self.REG_ARR2 + self.timer_index - 4

        self._write_register_16(
            register,
            rounded,
        )

    def get_period(
        self,
    ) -> int:
        return TIMER_STATE[self.timer_index]["period"]

    def set_pulse_width(
        self,
        pulse_width: float,
    ) -> None:
        value = self._require_finite_number(
            pulse_width,
            name="pulse_width",
        )

        rounded = int(value)

        if rounded < 0:
            raise PWMError("pulse_width must be greater than or equal to 0")

        period = self.get_period()

        if rounded > period:
            raise PWMError(f"pulse_width cannot be greater than period ({period})")

        self._pulse_width = rounded
        self._duty_cycle = rounded / period * 100

        register = self.REG_CHN + self.channel

        self._write_register_16(
            register,
            rounded,
        )

    def get_pulse_width(self) -> int:
        return self._pulse_width

    def set_duty_cycle(
        self,
        percent: float,
    ) -> None:
        value = self._require_finite_number(
            percent,
            name="duty cycle",
        )

        if not 0 <= value <= 100:
            raise PWMError("duty cycle must be between 0 and 100")

        pulse_width = value / 100.0 * self.get_period()

        self.set_pulse_width(pulse_width)

    def get_duty_cycle(
        self,
    ) -> float | None:
        return self._duty_cycle

    def off(self) -> None:
        self.set_duty_cycle(0)

    # Compatibility aliases

    def freq(
        self,
        frequency: float | None = None,
    ) -> float | None:
        if frequency is None:
            return self.get_frequency()

        self.set_frequency(frequency)
        return None

    def prescaler(
        self,
        prescaler: float | None = None,
    ) -> int | None:
        if prescaler is None:
            return self.get_prescaler()

        self.set_prescaler(prescaler)
        return None

    def period(
        self,
        period: float | None = None,
    ) -> int | None:
        if period is None:
            return self.get_period()

        self.set_period(period)
        return None

    def pulse_width(
        self,
        pulse_width: float | None = None,
    ) -> int | None:
        if pulse_width is None:
            return self.get_pulse_width()

        self.set_pulse_width(pulse_width)
        return None

    def pulse_width_percent(
        self,
        percent: float | None = None,
    ) -> float | None:
        if percent is None:
            return self.get_duty_cycle()

        self.set_duty_cycle(percent)
        return None

    def close(self) -> None:
        bus = self._i2c

        try:
            if self._owns_i2c and bus is not None:
                bus.close()
        finally:
            self._i2c = None

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        if self.closed:
            raise PWMError("Cannot enter a closed PWM")

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
