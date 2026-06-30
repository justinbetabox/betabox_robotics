#!/usr/bin/env python3

from time import sleep

from betabox_car.sensors import Grayscale

with Grayscale() as grayscale:
    print("\nGrayscale hardware test")
    print("=======================")

    for _ in range(10):
        values = grayscale.read()
        status = grayscale.status(values)

        print(f"values={values}, status={status}")
        sleep(0.3)

print("\nGrayscale hardware test complete.")
