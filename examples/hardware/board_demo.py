#!/usr/bin/env python3
"""
Betabox board mapping developer demo.

Displays the digital GPIO pins, PWM channels, ADC channels, and
compatibility aliases exposed by betabox_robotics.hardware.board.

This demo does not access physical hardware.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import IntEnum

from betabox_robotics.hardware.board import (
    ADC_CHANNELS,
    BOARD_PINS,
    PWM_CHANNELS,
    AnalogChannel,
    DigitalPin,
    Pins,
    PWMChannel,
)


def print_mapping(
    title: str,
    values: dict[str, int],
) -> None:
    print()
    print(title)
    print("-" * len(title))

    width = max(len(name) for name in values)

    for name, value in values.items():
        print(f"{name:<{width}}  {value}")


def print_enum(
    title: str,
    values: Iterable[IntEnum],
    *,
    value_prefix: str = "",
) -> None:
    print()
    print(title)
    print("-" * len(title))

    members = list(values)
    width = max(len(member.name) for member in members)

    for member in members:
        print(f"{member.name:<{width}}  {value_prefix}{int(member)}")


def print_aliases() -> None:
    aliases = {
        "SW": Pins.SW,
        "USER": Pins.USER,
        "LED": Pins.LED,
        "BOARD_TYPE": Pins.BOARD_TYPE,
        "RST": Pins.RST,
        "BLEINT": Pins.BLEINT,
        "BLERST": Pins.BLERST,
        "MCURST": Pins.MCURST,
        "CE": Pins.CE,
    }

    print()
    print("Board aliases")
    print("-------------")

    width = max(len(name) for name in aliases)

    for name, pin in aliases.items():
        print(f"{name:<{width}}  {pin.name} / GPIO{int(pin)}")


def print_duplicate_gpio_assignments() -> None:
    grouped: dict[int, list[str]] = {}

    for name, gpio_number in BOARD_PINS.items():
        grouped.setdefault(
            gpio_number,
            [],
        ).append(name)

    duplicates = {
        gpio_number: names for gpio_number, names in grouped.items() if len(names) > 1
    }

    print()
    print("Shared GPIO assignments")
    print("-----------------------")

    if not duplicates:
        print("No GPIO aliases detected.")
        return

    for gpio_number, names in sorted(duplicates.items()):
        print(f"GPIO{gpio_number}: {', '.join(names)}")


def print_compatibility_examples() -> None:
    print()
    print("Compatibility examples")
    print("----------------------")

    print(
        "Pins.D0 == DigitalPin.D0:",
        Pins.D0 == DigitalPin.D0,
    )
    print(
        "Pins.P0 == PWMChannel.P0:",
        Pins.P0 == PWMChannel.P0,
    )
    print(
        "Pins.A0 == AnalogChannel.A0:",
        Pins.A0 == AnalogChannel.A0,
    )

    print()
    print(
        "Digital pins can be converted to integers:",
        int(Pins.D0),
    )
    print(
        "PWM channels can be converted to integers:",
        int(Pins.P0),
    )
    print(
        "ADC channels can be converted to integers:",
        int(Pins.A0),
    )


def main() -> None:
    print()
    print("Betabox board mapping demo")
    print("==========================")
    print()
    print(
        "This demo displays software mappings only. "
        "It does not open GPIO or I²C hardware."
    )

    print_enum(
        "Digital pins",
        DigitalPin,
        value_prefix="GPIO",
    )

    print_enum(
        "PWM channels",
        PWMChannel,
    )

    print_enum(
        "ADC channels",
        AnalogChannel,
    )

    print_aliases()
    print_duplicate_gpio_assignments()
    print_compatibility_examples()

    print_mapping(
        "BOARD_PINS dictionary",
        BOARD_PINS,
    )

    print_mapping(
        "PWM_CHANNELS dictionary",
        PWM_CHANNELS,
    )

    print_mapping(
        "ADC_CHANNELS dictionary",
        ADC_CHANNELS,
    )

    print()
    print("Board mapping demo complete.")


if __name__ == "__main__":
    main()
