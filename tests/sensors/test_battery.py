#!/usr/bin/env python3
"""
Betabox Battery validation test.

Validates battery voltage monitoring and status reporting.
"""

from time import sleep

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import Battery


def main() -> None:
    with Battery.default(BETABOX_CAR.sensors.battery) as battery:
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
