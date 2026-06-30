import logging
from typing import List, Optional, Union

from .board import ADC_CHANNELS, AnalogChannel
from .exceptions import HardwareError
from .i2c import I2C


class ADCError(HardwareError):
    """Raised when an ADC operation fails."""


class ADC:
    """
    Betabox ADC channel abstraction.

    Reads analog channels from the Robot HAT controller.
    """

    ADDRESSES = [0x14, 0x15]
    MAX_VALUE = 4095
    REFERENCE_VOLTAGE = 3.3

    def __init__(
        self,
        channel: Union[int, str, AnalogChannel],
        address: Optional[Union[int, List[int]]] = None,
        bus: Optional[I2C] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        self.channel = self._resolve_channel(channel)
        self.register = self._channel_to_register(self.channel)

        self._i2c = bus or I2C(address=address or self.ADDRESSES)
        self._owns_i2c = bus is None

    def _resolve_channel(self, channel: Union[int, str, AnalogChannel]) -> int:
        if isinstance(channel, AnalogChannel):
            return channel.value

        if isinstance(channel, str):
            if channel not in ADC_CHANNELS:
                raise ADCError(
                    f'Unknown ADC channel "{channel}". Valid channels: {list(ADC_CHANNELS.keys())}'
                )
            return ADC_CHANNELS[channel]

        if isinstance(channel, int):
            if channel not in ADC_CHANNELS.values():
                raise ADCError(f"ADC channel must be in range 0-7, not {channel}")
            return channel

        raise ADCError("channel must be an int, string channel name, or AnalogChannel")

    def _channel_to_register(self, channel: int) -> int:
        # Preserve Robot HAT behavior:
        # channel order is inverted, then OR'd with 0x10.
        inverted = 7 - channel
        return inverted | 0x10

    def _bus(self) -> I2C:
        if self._i2c is None:
            raise ADCError("ADC I2C bus is closed")

        return self._i2c

    def read(self) -> int:
        self._bus().write([self.register, 0, 0])
        msb, lsb = self._bus().read(2)
        value = (msb << 8) + lsb

        self.logger.debug("ADC channel=%s value=%s", self.channel, value)

        return value

    def read_voltage(self) -> float:
        value = self.read()
        voltage = value * self.REFERENCE_VOLTAGE / self.MAX_VALUE

        self.logger.debug("ADC channel=%s voltage=%s", self.channel, voltage)

        return voltage

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
