#!/usr/bin/env python3
"""
Betabox Ultrasonic validation test.

Validates distance measurement using the configured Ultrasonic sensor.
"""

from time import sleep

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import (
    Ultrasonic,
    UltrasonicReadError,
    UltrasonicTimeoutError,
)


def main() -> None:
    with Ultrasonic.default(BETABOX_CAR.sensors.ultrasonic) as sensor:
        print("\nUltrasonic validation test")
        print("==========================")

        for _ in range(10):
            try:
                distance = sensor.distance()
                print(f"Distance: {distance:.2f} cm")

            except UltrasonicTimeoutError:
                print("Status  : timeout")

            except UltrasonicReadError:
                print("Status  : invalid pulse")

            sleep(0.3)

    print("\nUltrasonic validation test complete.")


if __name__ == "__main__":
    main()
