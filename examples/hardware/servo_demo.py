#!/usr/bin/env python3
"""
Developer demo for the Betabox Servo hardware abstraction.
"""

from time import sleep

from betabox_robotics.hardware import Pins, Servo


def main() -> None:
    print()
    print("Betabox Servo Demo")
    print("==================")
    print()

    with Servo(Pins.P0) as servo:
        print("Centering servo...")
        servo.center()
        sleep(1)

        print("Moving to -45°...")
        servo.move_to(-45)
        sleep(1)

        print("Moving to 45°...")
        servo.move_to(45)
        sleep(1)

        print("Returning to center...")
        servo.center()
        sleep(1)

        print("Moving immediately to 30°...")
        servo.move_to(30, smooth=False)
        sleep(1)

        print("Centering servo...")
        servo.center()

    print()
    print("Servo demo complete.")


if __name__ == "__main__":
    main()
