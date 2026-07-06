#!/usr/bin/env python3
"""
Betabox Steering validation test.

Validates steering movement independently of the drive motors.
Only the steering servo should move.
"""

from time import sleep

from betabox_robotics.drive import Drive
from betabox_robotics.robots import BETABOX_CAR


def main() -> None:
    drive = Drive.default(BETABOX_CAR)

    try:
        print("\nSteering validation test")
        print("========================")
        print("Only the steering servo should move.")
        print("Camera pan/tilt servos should NOT move.\n")

        print("Center")
        drive.center()
        sleep(2)

        print("Left 20°")
        drive.left(20)
        sleep(2)

        print("Right 20°")
        drive.right(20)
        sleep(2)

        print("Center")
        drive.center()
        sleep(2)

    finally:
        drive.close()

    print("\nSteering validation test complete.")


if __name__ == "__main__":
    main()
