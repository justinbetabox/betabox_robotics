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
            BETABOX_CAR.drive.steering.servo,
            min_angle=BETABOX_CAR.drive.steering.min_angle,
            max_angle=BETABOX_CAR.drive.steering.max_angle,
        ),
        "pan": Servo(
            BETABOX_CAR.camera_mount.pan_servo,
            min_angle=(
                BETABOX_CAR
                .camera_mount
                .pan_min_angle
            ),
            max_angle=(
                BETABOX_CAR
                .camera_mount
                .pan_max_angle
            ),
        ),
        "tilt": Servo(
            BETABOX_CAR.camera_mount.tilt_servo,
            min_angle=(
                BETABOX_CAR
                .camera_mount
                .tilt_min_angle
            ),
            max_angle=(
                BETABOX_CAR
                .camera_mount
                .tilt_max_angle
            ),
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
