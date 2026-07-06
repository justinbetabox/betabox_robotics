#!/usr/bin/env python3
"""
Developer demo for the Betabox Grayscale sensor.
"""

from time import sleep

from betabox_car.robots import BETABOX_CAR
from betabox_car.sensors import Grayscale


def main() -> None:
    print()
    print("Betabox Grayscale Demo")
    print("======================")
    print()

    with Grayscale.default(BETABOX_CAR) as grayscale:
        while True:
            values = grayscale.read()
            status = grayscale.status(values)

            print(f"Values: {values}")
            print(f"Status: {status}")
            print()

            sleep(0.5)


if __name__ == "__main__":
    main()
