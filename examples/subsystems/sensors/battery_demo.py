#!/usr/bin/env python3
"""
Developer demo for the Betabox Battery sensor.
"""

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import Battery


def main() -> None:
    print()
    print("Betabox Battery Demo")
    print("====================")
    print()

    with Battery.default(BETABOX_CAR.sensors.battery) as battery:
        voltage = battery.voltage()
        status = battery.status()

        print(f"Battery Voltage: {voltage:.2f} V")
        print(f"Battery Status : {status}")

        if battery.is_critical():
            print("Battery is critically low.")
        elif battery.is_low():
            print("Battery is low.")
        else:
            print("Battery level is good.")

    print()
    print("Battery demo complete.")


if __name__ == "__main__":
    main()
