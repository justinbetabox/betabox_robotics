#!/usr/bin/env python3
"""
Betabox Motor Demo

Demonstrates one motor at a time and both motors together.

Press Ctrl+C at any time to stop.
"""

from time import sleep

from betabox_car.hardware import PWM, Motor, Pin, Pins


def pause(seconds=1):
    sleep(seconds)


def main():
    left = Motor(
        PWM(Pins.P13),
        Pin(Pins.D4, mode=Pin.OUT),
        reversed=True,
    )

    right = Motor(
        PWM(Pins.P12),
        Pin(Pins.D5, mode=Pin.OUT),
        reversed=False,
    )

    try:
        print("Motor demo starting...")

        print("Left motor forward")
        left.forward(40)
        pause()
        left.stop()

        print("Left motor backward")
        left.backward(40)
        pause()
        left.stop()

        print("Right motor forward")
        right.forward(40)
        pause()
        right.stop()

        print("Right motor backward")
        right.backward(40)
        pause()
        right.stop()

        print("Both motors forward")
        left.forward(40)
        right.forward(40)
        pause(2)

        print("Both motors backward")
        left.backward(40)
        right.backward(40)
        pause(2)

        print("Stopping")
        left.stop()
        right.stop()

        print("Demo complete.")

    except KeyboardInterrupt:
        print("\nInterrupted. Stopping motors.")
        left.stop()
        right.stop()

    finally:
        left.close()
        right.close()


if __name__ == "__main__":
    main()
