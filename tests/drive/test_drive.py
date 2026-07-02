#!/usr/bin/env python3
"""
Betabox Drive validation test.

Validates:
- Forward
- Backward
- Steering
- Stop
"""

from time import sleep

from betabox_car.drive import Drive
from betabox_car.robots import BETABOX_CAR


def main() -> None:
    drive = Drive.default(BETABOX_CAR)

    try:
        print("\nDrive validation test")
        print("=====================")

        print("Center steering")
        drive.center()
        sleep(1)

        print("Forward")
        drive.forward(30)
        sleep(2)

        print("Stop")
        drive.stop()
        sleep(1)

        print("Backward")
        drive.backward(30)
        sleep(2)

        print("Stop")
        drive.stop()
        sleep(1)

        print("Left")
        drive.left(20)
        sleep(1)

        print("Right")
        drive.right(20)
        sleep(1)

        print("Center")
        drive.center()

    finally:
        drive.close()

    print("\nDrive validation test complete.")


if __name__ == "__main__":
    main()
