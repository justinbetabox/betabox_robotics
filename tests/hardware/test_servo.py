#!/usr/bin/env python3

from time import sleep

from betabox_car.hardware import Pins, Servo

servos = {
    "steering": Servo(
        Pins.P2,
        min_angle=-30,
        max_angle=30,
    ),
    "pan": Servo(
        Pins.P0,
        min_angle=-45,
        max_angle=45,
    ),
    "tilt": Servo(
        Pins.P1,
        min_angle=-30,
        max_angle=45,
    ),
}

try:
    for name, servo in servos.items():
        print(f"\nTesting {name}")

        print("  Center")
        servo.center()
        sleep(1)

        print("  Minimum")
        servo.min()
        sleep(1)

        print("  Maximum")
        servo.max()
        sleep(1)

        print("  Return to center")
        servo.center()
        sleep(1)

finally:
    for servo in servos.values():
        servo.close()

print("\nServo hardware test complete.")
