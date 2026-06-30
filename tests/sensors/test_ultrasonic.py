#!/usr/bin/env python3

from time import sleep

from betabox_car.sensors import Ultrasonic

with Ultrasonic() as sensor:
    print("\nUltrasonic hardware test")
    print("========================")

    for _ in range(10):
        distance = sensor.distance()

        if distance == -1:
            print("timeout")
        elif distance == -2:
            print("invalid pulse")
        else:
            print(f"{distance:.2f} cm")

        sleep(0.3)

print("\nUltrasonic hardware test complete.")
