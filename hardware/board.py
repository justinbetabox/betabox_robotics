"""
Board-level hardware identifiers.

These enums define the logical Betabox pin and channel names used
throughout the library. Digital pin values use Raspberry Pi BCM
numbering, while PWM and analog values identify Robot HAT channels.
"""

from __future__ import annotations

from enum import IntEnum
from typing import NoReturn


class DigitalPin(IntEnum):
    """Raspberry Pi BCM GPIO identifiers used by the Robot HAT."""

    D0 = 17
    D1 = 4
    D2 = 27
    D3 = 22
    D4 = 23
    D5 = 24
    D6 = 25

    # D7 intentionally shares BCM GPIO 4 with D1 for compatibility
    # with the original Robot HAT board mapping.
    D7 = 4

    D8 = 5
    D9 = 6
    D10 = 12
    D11 = 13
    D12 = 19
    D13 = 16
    D14 = 26
    D15 = 20
    D16 = 21

    # Named board-function aliases.
    SW = 25
    USER = 25
    LED = 26
    BOARD_TYPE = 12
    RST = 16
    BLEINT = 13
    BLERST = 20
    MCURST = 5
    CE = 8


class PWMChannel(IntEnum):
    """Robot HAT PWM channel identifiers."""

    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4
    P5 = 5
    P6 = 6
    P7 = 7
    P8 = 8
    P9 = 9
    P10 = 10
    P11 = 11
    P12 = 12
    P13 = 13
    P14 = 14
    P15 = 15
    P16 = 16
    P17 = 17
    P18 = 18
    P19 = 19


class AnalogChannel(IntEnum):
    """Robot HAT analog-to-digital converter channel identifiers."""

    A0 = 0
    A1 = 1
    A2 = 2
    A3 = 3
    A4 = 4
    A5 = 5
    A6 = 6
    A7 = 7


class Pins:
    """
    Compatibility namespace containing all board identifiers.

    Prefer the specific DigitalPin, PWMChannel, and AnalogChannel enums
    in new internal code. Pins remains available as a convenient combined
    namespace for public and compatibility APIs.
    """

    def __new__(cls) -> NoReturn:
        raise TypeError("Pins is a namespace and cannot be instantiated")

    D0 = DigitalPin.D0
    D1 = DigitalPin.D1
    D2 = DigitalPin.D2
    D3 = DigitalPin.D3
    D4 = DigitalPin.D4
    D5 = DigitalPin.D5
    D6 = DigitalPin.D6
    D7 = DigitalPin.D7
    D8 = DigitalPin.D8
    D9 = DigitalPin.D9
    D10 = DigitalPin.D10
    D11 = DigitalPin.D11
    D12 = DigitalPin.D12
    D13 = DigitalPin.D13
    D14 = DigitalPin.D14
    D15 = DigitalPin.D15
    D16 = DigitalPin.D16

    A0 = AnalogChannel.A0
    A1 = AnalogChannel.A1
    A2 = AnalogChannel.A2
    A3 = AnalogChannel.A3
    A4 = AnalogChannel.A4
    A5 = AnalogChannel.A5
    A6 = AnalogChannel.A6
    A7 = AnalogChannel.A7

    SW = DigitalPin.SW
    USER = DigitalPin.USER
    LED = DigitalPin.LED
    BOARD_TYPE = DigitalPin.BOARD_TYPE
    RST = DigitalPin.RST
    BLEINT = DigitalPin.BLEINT
    BLERST = DigitalPin.BLERST
    MCURST = DigitalPin.MCURST
    CE = DigitalPin.CE

    P0 = PWMChannel.P0
    P1 = PWMChannel.P1
    P2 = PWMChannel.P2
    P3 = PWMChannel.P3
    P4 = PWMChannel.P4
    P5 = PWMChannel.P5
    P6 = PWMChannel.P6
    P7 = PWMChannel.P7
    P8 = PWMChannel.P8
    P9 = PWMChannel.P9
    P10 = PWMChannel.P10
    P11 = PWMChannel.P11
    P12 = PWMChannel.P12
    P13 = PWMChannel.P13
    P14 = PWMChannel.P14
    P15 = PWMChannel.P15
    P16 = PWMChannel.P16
    P17 = PWMChannel.P17
    P18 = PWMChannel.P18
    P19 = PWMChannel.P19


# Use __members__ rather than enum iteration so aliases such as D7,
# SW, and USER remain available through string-based lookup.
BOARD_PINS: dict[str, int] = {
    name: member.value for name, member in DigitalPin.__members__.items()
}

PWM_CHANNELS: dict[str, int] = {
    name: member.value for name, member in PWMChannel.__members__.items()
}

ADC_CHANNELS: dict[str, int] = {
    name: member.value for name, member in AnalogChannel.__members__.items()
}
