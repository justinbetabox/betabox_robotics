#!/usr/bin/env python3
"""
Developer demo for the Betabox ADC hardware abstraction.
"""

from time import sleep

from betabox_car.hardware import ADC, Pins


def main() -> None:
    print()
    print("Betabox ADC Demo")
    print("================")
    print()

    with ADC(Pins.A0) as adc:
        while True:
            value = adc.read()
            voltage = adc.read_voltage()

            print(f"Value:   {value}")
            print(f"Voltage: {voltage:.3f} V")
            print()

            sleep(0.5)


if __name__ == "__main__":
    main()
