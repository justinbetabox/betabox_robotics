#!/usr/bin/env python3
"""
Betabox Ultrasonic validation test.

Validates distance measurement using the Ultrasonic sensor subsystem.
"""

from time import sleep

from betabox_car.robots import BETABOX_CAR
from betabox_car.sensors import Ultrasonic


def main() -> None:
    with Ultrasonic(
        trigger=BETABOX_CAR.ultrasonic.trigger,
        echo=BETABOX_CAR.ultrasonic.echo,
    ) as sensor:
        print("\nUltrasonic validation test")
        print("==========================")

        for _ in range(10):
            distance = sensor.distance()

            if distance == -1:
                print("Status  : timeout")
            elif distance == -2:
                print("Status  : invalid pulse")
            else:
                print(f"Distance: {distance:.2f} cm")

            sleep(0.3)

    print("\nUltrasonic validation test complete.")


if __name__ == "__main__":
    main()
