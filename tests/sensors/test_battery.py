#!/usr/bin/env python3
"""
Betabox Battery validation test.

Validates battery voltage monitoring and status reporting.
"""

from time import sleep

from betabox_car.hardware import ADC
from betabox_car.robots import BETABOX_CAR
from betabox_car.sensors import Battery


def main() -> None:
    with Battery(
        adc=ADC(BETABOX_CAR.battery.channel),
        scale=BETABOX_CAR.battery.scale,
        low_voltage=BETABOX_CAR.battery.low_voltage,
        critical_voltage=BETABOX_CAR.battery.critical_voltage,
    ) as battery:
        print("\nBattery validation test")
        print("=======================")

        for _ in range(10):
            voltage = battery.voltage()
            status = battery.status()

            print(f"Voltage: {voltage:.2f} V")
            print(f"Status : {status}")
            print()

            sleep(0.5)

    print("Battery validation test complete.")


if __name__ == "__main__":
    main()
