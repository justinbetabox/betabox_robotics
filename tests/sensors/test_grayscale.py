#!/usr/bin/env python3
"""
Betabox Grayscale validation test.

Validates grayscale sensor readings and line/floor status reporting.
"""

from time import sleep

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import Grayscale


def main() -> None:
    with Grayscale.default(BETABOX_CAR.sensors.grayscale) as grayscale:
        print("\nGrayscale validation test")
        print("=========================")

        for _ in range(10):
            values = grayscale.read()
            status = grayscale.status(values)

            print(f"Values: {values}")
            print(f"Status: {status}")
            print()

            sleep(0.3)

    print("Grayscale validation test complete.")


if __name__ == "__main__":
    main()
