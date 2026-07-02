#!/usr/bin/env python3
"""
Developer demo for the Betabox Ultrasonic sensor.
"""

from time import sleep

from betabox_car.robots import BETABOX_CAR
from betabox_car.sensors import Ultrasonic


def main() -> None:
    print()
    print("Betabox Ultrasonic Demo")
    print("=======================")
    print()

    with Ultrasonic.default(BETABOX_CAR) as sensor:
        while True:
            distance = sensor.distance()

            if distance < 0:
                print("No reading")
            else:
                print(f"Distance: {distance:.2f} cm")

            sleep(0.5)


if __name__ == "__main__":
    main()
