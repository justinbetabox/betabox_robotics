#!/usr/bin/env python3
"""
Betabox ADC developer demo.

Reads every Robot HAT analog channel and reports both the raw ADC value
and the converted reference voltage.

This demo validates:

- ADC channel resolution;
- shared I²C bus injection;
- raw ADC reads;
- voltage conversion;
- repeated sampling;
- context-managed cleanup.

The voltage shown is the ADC input voltage calculated against the
controller's 3.3 V reference. Higher-level sensors may apply their own
scaling after this value is read.
"""

from __future__ import annotations

from contextlib import ExitStack
from time import sleep

from betabox_robotics.hardware import (
    ADC,
    I2C,
    ADCError,
    HardwareError,
    Pins,
)

I2C_BUS_NUMBER = 1
SAMPLE_COUNT = 5
SAMPLE_DELAY = 0.5

CHANNELS = (
    Pins.A0,
    Pins.A1,
    Pins.A2,
    Pins.A3,
    Pins.A4,
    Pins.A5,
    Pins.A6,
    Pins.A7,
)


def print_channel_header() -> None:
    print()
    print(f"{'Channel':<9}{'Register':<11}{'Raw':>8}{'Voltage':>12}")
    print("-" * 40)


def print_reading(
    adc: ADC,
) -> None:
    raw_value = adc.read()

    voltage = raw_value * ADC.REFERENCE_VOLTAGE / ADC.MAX_VALUE

    print(
        f"A{adc.channel:<8}0x{adc.register:02X}{'':<7}{raw_value:>8}{voltage:>10.3f} V"
    )


def main() -> int:
    print()
    print("Betabox ADC demo")
    print("================")
    print()
    print(f"I²C bus: /dev/i2c-{I2C_BUS_NUMBER}")
    print("Channels: " + ", ".join(channel.name for channel in CHANNELS))
    print(f"ADC range: 0-{ADC.MAX_VALUE}; reference: {ADC.REFERENCE_VOLTAGE:.1f} V")
    print()
    print(
        "This demo repeatedly samples all analog inputs. "
        "It does not modify ADC configuration."
    )

    try:
        with ExitStack() as stack:
            bus = stack.enter_context(
                I2C(
                    address=ADC.ADDRESSES,
                    bus=I2C_BUS_NUMBER,
                )
            )

            adcs = [
                stack.enter_context(
                    ADC(
                        channel,
                        bus=bus,
                    )
                )
                for channel in CHANNELS
            ]

            print()
            print(f"Shared I²C bus open: {not bus.closed}")

            for sample_number in range(
                1,
                SAMPLE_COUNT + 1,
            ):
                print()
                print(f"Sample {sample_number}/{SAMPLE_COUNT}")

                print_channel_header()

                for adc in adcs:
                    print_reading(adc)

                if sample_number < SAMPLE_COUNT:
                    sleep(SAMPLE_DELAY)

            print()
            print(
                "ADC objects borrow the shared I²C bus, "
                "so closing them does not close the bus."
            )

        print()
        print(f"Shared I²C bus closed after context exit: {bus.closed}")

    except ADCError as exc:
        print()
        print(f"ADC demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"ADC demo failed: {type(exc).__name__}: {exc}")
        return 1

    print()
    print("ADC demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
