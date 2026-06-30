#!/usr/bin/env python3

"""
Betabox Motor Hardware Test

Tests:
- Forward
- Backward
- Stop
- Speed ramping
- Both motors together
"""

from time import sleep

from betabox_car.hardware import (
    PWM,
    Motor,
    Pin,
    Pins,
)

LEFT = Motor(
    PWM(Pins.P13),
    Pin(Pins.D4, mode=Pin.OUT),
    reversed=True,
)

RIGHT = Motor(
    PWM(Pins.P12),
    Pin(Pins.D5, mode=Pin.OUT),
)


def pause():
    sleep(1)


try:
    print("\n==============================")
    print(" Left Motor")
    print("==============================")

    print("Forward 30%")
    LEFT.forward(30)
    pause()

    print("Stop")
    LEFT.stop()
    pause()

    print("Backward 30%")
    LEFT.backward(30)
    pause()

    print("Stop")
    LEFT.stop()
    pause()

    print("\n==============================")
    print(" Right Motor")
    print("==============================")

    print("Forward 30%")
    RIGHT.forward(30)
    pause()

    print("Stop")
    RIGHT.stop()
    pause()

    print("Backward 30%")
    RIGHT.backward(30)
    pause()

    print("Stop")
    RIGHT.stop()
    pause()

    print("\n==============================")
    print(" Both Motors Forward")
    print("==============================")

    LEFT.forward(30)
    RIGHT.forward(30)
    pause()

    LEFT.stop()
    RIGHT.stop()
    pause()

    print("\n==============================")
    print(" Both Motors Backward")
    print("==============================")

    LEFT.backward(30)
    RIGHT.backward(30)
    pause()

    LEFT.stop()
    RIGHT.stop()
    pause()

    print("\n==============================")
    print(" Counter Rotation")
    print("==============================")

    LEFT.forward(30)
    RIGHT.backward(30)
    pause()

    LEFT.stop()
    RIGHT.stop()
    pause()

    LEFT.backward(30)
    RIGHT.forward(30)
    pause()

    LEFT.stop()
    RIGHT.stop()
    pause()

    print("\n==============================")
    print(" Ramp Test")
    print("==============================")

    for speed in range(0, 101, 10):
        print(f"{speed}%")
        LEFT.forward(speed)
        RIGHT.forward(speed)
        sleep(0.25)

    for speed in range(100, -1, -10):
        print(f"{speed}%")
        LEFT.forward(speed)
        RIGHT.forward(speed)
        sleep(0.25)

    LEFT.stop()
    RIGHT.stop()

finally:
    LEFT.close()
    RIGHT.close()

print("\nMotor hardware test complete.")
