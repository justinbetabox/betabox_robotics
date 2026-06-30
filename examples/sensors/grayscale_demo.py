#!/usr/bin/env python3

from time import sleep

from betabox_car.sensors import Grayscale

with Grayscale() as grayscale:
    while True:
        values = grayscale.read()
        status = grayscale.status(values)

        print(f"values={values}, status={status}")
        sleep(0.5)
