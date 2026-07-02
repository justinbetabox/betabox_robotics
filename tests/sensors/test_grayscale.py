#!/usr/bin/env python3
"""
Betabox Grayscale validation test.

Validates grayscale sensor readings and line/floor status reporting.
"""

from time import sleep

from betabox_car.hardware import ADC
from betabox_car.robots import BETABOX_CAR
from betabox_car.sensors import Grayscale


def main() -> None:
    with Grayscale(
        left=ADC(BETABOX_CAR.grayscale.left),
        middle=ADC(BETABOX_CAR.grayscale.middle),
        right=ADC(BETABOX_CAR.grayscale.right),
    ) as grayscale:
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
