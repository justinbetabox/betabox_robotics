#!/usr/bin/env python3
"""
Betabox Servo hardware test.

Exercises the steering, pan, and tilt servos.
"""

from time import sleep

from betabox_robotics.hardware import Pins, Servo
from betabox_robotics.robots import BETABOX_CAR


def main() -> None:
    servos = {
        "steering": Servo(
            BETABOX_CAR.steering.servo,
            min_angle=BETABOX_CAR.steering.min_angle,
            max_angle=BETABOX_CAR.steering.max_angle,
        ),
        "pan": Servo(
            Pins.P0,
            min_angle=-45,
            max_angle=45,
        ),
        "tilt": Servo(
            Pins.P1,
            min_angle=-30,
            max_angle=45,
        ),
    }

    try:
        print("\nServo hardware test")
        print("===================")

        for name, servo in servos.items():
            print(f"\nTesting {name}")

            print("  Center")
            servo.center()
            sleep(1)

            print("  Minimum")
            servo.min()
            sleep(1)

            print("  Maximum")
            servo.max()
            sleep(1)

            print("  Return to center")
            servo.center()
            sleep(1)

    finally:
        for servo in servos.values():
            servo.close()

    print("\nServo hardware test complete.")


if __name__ == "__main__":
    main()
