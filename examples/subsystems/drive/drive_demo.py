#!/usr/bin/env python3
"""
Developer demo for the Betabox Drive subsystem.
"""

from time import sleep

from betabox_robotics.drive import Drive
from betabox_robotics.robots import BETABOX_CAR


def main() -> None:
    print()
    print("Betabox Drive Demo")
    print("==================")
    print()

    with Drive.default(BETABOX_CAR) as drive:
        try:
            print("Centering steering...")
            drive.center()
            sleep(1)

            print("Driving forward...")
            drive.forward(40)
            sleep(2)

            print("Stopping...")
            drive.stop()
            sleep(1)

            print("Turning left...")
            drive.left(20)
            sleep(1)

            print("Driving forward...")
            drive.forward(30)
            sleep(2)
        finally:
            print("Stopping and centering...")
            drive.stop()
            drive.center()

    print()
    print("Drive demo complete.")


if __name__ == "__main__":
    main()
