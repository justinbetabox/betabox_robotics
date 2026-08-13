from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import ClassVar, Self

from .board import ADC_CHANNELS, AnalogChannel
from .exceptions import HardwareError
from .i2c import I2C


class ADCError(HardwareError):
    """Raised when an ADC operation fails."""


class ADC:
    """
    Betabox ADC channel abstraction.

    Reads analog channels from the Robot HAT controller over I²C.
    An ADC created without an injected I²C bus owns and closes that bus.
    An injected bus is borrowed and remains owned by the caller.
    """

    logger: logging.Logger
    channel: int
    register: int

    _i2c: I2C | None
    _owns_i2c: bool

    ADDRESSES: ClassVar[tuple[int, ...]] = (
        0x14,
        0x15,
    )

    MAX_VALUE: ClassVar[int] = 4095
    REFERENCE_VOLTAGE: ClassVar[float] = 3.3

    def __init__(
        self,
        channel: int | str | AnalogChannel,
        address: int | Sequence[int] | None = None,
        bus: I2C | None = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        self.channel = self._resolve_channel(channel)
        self.register = self._channel_to_register(self.channel)

        self._i2c = None
        self._owns_i2c = bus is None

        try:
            self._i2c = (
                bus
                if bus is not None
                else I2C(address=(self.ADDRESSES if address is None else address))
            )
        except (
            HardwareError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            self.close()
            raise

    @staticmethod
    def _resolve_channel(
        channel: int | str | AnalogChannel,
    ) -> int:
        if isinstance(channel, AnalogChannel):
            return int(channel)

        if isinstance(channel, str):
            try:
                return ADC_CHANNELS[channel]
            except KeyError:
                valid_channels = ", ".join(ADC_CHANNELS)

                raise ADCError(
                    f'Unknown ADC channel "{channel}". Valid channels: {valid_channels}'
                ) from None

        if isinstance(channel, bool):
            raise TypeError(
                "channel must be an int, string channel name, or AnalogChannel"
            )

        if channel not in ADC_CHANNELS.values():
            raise ADCError(f"ADC channel must be in range 0-7, not {channel}")

        return channel

    @staticmethod
    def _channel_to_register(
        channel: int,
    ) -> int:
        if not 0 <= channel <= 7:
            raise ADCError("ADC channel must be in range 0-7")

        # Preserve Robot HAT behavior:
        # channel order is inverted, then OR'd with 0x10.
        inverted = 7 - channel
        return inverted | 0x10

    @property
    def closed(self) -> bool:
        return self._i2c is None

    def _bus(self) -> I2C:
        bus = self._i2c

        if bus is None:
            raise ADCError("ADC I2C bus is closed")

        return bus

    def read(self) -> int:
        bus = self._bus()

        bus.write(
            [
                self.register,
                0,
                0,
            ]
        )

        data = bus.read(2)

        if len(data) != 2:
            raise ADCError(
                f"ADC read returned an unexpected number of bytes: {len(data)}"
            )

        msb, lsb = data
        value = (msb << 8) + lsb

        self.logger.debug(
            "ADC channel=%s value=%s",
            self.channel,
            value,
        )

        return value

    def read_voltage(self) -> float:
        value = self.read()

        voltage = value * self.REFERENCE_VOLTAGE / self.MAX_VALUE

        self.logger.debug(
            "ADC channel=%s voltage=%s",
            self.channel,
            voltage,
        )

        return voltage

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
            raise ADCError("Cannot enter a closed ADC")

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
