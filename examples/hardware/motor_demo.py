#!/usr/bin/env python3
"""
Developer demo for the Betabox Motor hardware abstraction.
"""

from time import sleep

from betabox_robotics.hardware import PWM, Motor, Pin
from betabox_robotics.robots import BETABOX_CAR


def pause(seconds: float = 1.0) -> None:
    sleep(seconds)


def main() -> None:
    print()
    print("Betabox Motor Demo")
    print("==================")
    print()

    left_cfg = BETABOX_CAR.left_motor
    right_cfg = BETABOX_CAR.right_motor

    left = Motor(
        PWM(left_cfg.pwm),
        Pin(left_cfg.direction, mode=Pin.OUT),
        reversed=left_cfg.reversed,
    )

    right = Motor(
        PWM(right_cfg.pwm),
        Pin(right_cfg.direction, mode=Pin.OUT),
        reversed=right_cfg.reversed,
    )

    try:
        print("Left motor forward...")
        left.forward(40)
        pause()
        left.stop()

        print("Left motor backward...")
        left.backward(40)
        pause()
        left.stop()

        print("Right motor forward...")
        right.forward(40)
        pause()
        right.stop()

        print("Right motor backward...")
        right.backward(40)
        pause()
        right.stop()

        print("Both motors forward...")
        left.forward(40)
        right.forward(40)
        pause(2)

        print("Both motors backward...")
        left.backward(40)
        right.backward(40)
        pause(2)

    except KeyboardInterrupt:
        print()
        print("Interrupted. Stopping motors...")

    finally:
        left.stop()
        right.stop()
        left.close()
        right.close()

    print()
    print("Motor demo complete.")


if __name__ == "__main__":
    main()
