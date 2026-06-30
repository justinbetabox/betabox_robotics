#!/usr/bin/env python3

from time import sleep

from betabox_car.hardware import Pins, Servo

servo = Servo(Pins.P0)

try:
    print("Center")
    servo.center()
    sleep(1)

    print("Move to -45°")
    servo.move_to(-45)
    sleep(1)

    print("Move to 45°")
    servo.move_to(45)
    sleep(1)

    print("Return to center")
    servo.center()
    sleep(1)

    print("Immediate move to 30°")
    servo.move_to(30, smooth=False)
    sleep(1)

    print("Center")
    servo.center()

finally:
    servo.close()

print("Servo demo complete.")
