#!/usr/bin/env python3

from time import sleep

from betabox_car.sensors import Ultrasonic

with Ultrasonic() as sensor:
    while True:
        distance = sensor.distance()

        if distance < 0:
            print("No reading")
        else:
            print(f"Distance: {distance:.2f} cm")

        sleep(0.5)
