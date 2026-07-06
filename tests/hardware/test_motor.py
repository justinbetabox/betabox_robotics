#!/usr/bin/env python3
"""
Betabox Motor hardware test.

Tests:
- Forward
- Backward
- Stop
- Speed ramping
- Both motors together
"""

from time import sleep

from betabox_robotics.hardware import PWM, Motor, Pin
from betabox_robotics.robots import BETABOX_CAR


def pause(seconds: float = 1.0) -> None:
    sleep(seconds)


def main() -> None:
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
        print("\nMotor hardware test")
        print("===================")

        print("\nLeft motor")
        print("----------")

        print("Forward 30%")
        left.forward(30)
        pause()

        print("Stop")
        left.stop()
        pause()

        print("Backward 30%")
        left.backward(30)
        pause()

        print("Stop")
        left.stop()
        pause()

        print("\nRight motor")
        print("-----------")

        print("Forward 30%")
        right.forward(30)
        pause()

        print("Stop")
        right.stop()
        pause()

        print("Backward 30%")
        right.backward(30)
        pause()

        print("Stop")
        right.stop()
        pause()

        print("\nBoth motors forward")
        print("-------------------")

        left.forward(30)
        right.forward(30)
        pause()

        left.stop()
        right.stop()
        pause()

        print("\nBoth motors backward")
        print("--------------------")

        left.backward(30)
        right.backward(30)
        pause()

        left.stop()
        right.stop()
        pause()

        print("\nCounter rotation")
        print("----------------")

        left.forward(30)
        right.backward(30)
        pause()

        left.stop()
        right.stop()
        pause()

        left.backward(30)
        right.forward(30)
        pause()

        left.stop()
        right.stop()
        pause()

        print("\nRamp test")
        print("---------")

        for speed in range(0, 101, 10):
            print(f"{speed}%")
            left.forward(speed)
            right.forward(speed)
            sleep(0.25)

        for speed in range(100, -1, -10):
            print(f"{speed}%")
            left.forward(speed)
            right.forward(speed)
            sleep(0.25)

        left.stop()
        right.stop()

    finally:
        left.close()
        right.close()

    print("\nMotor hardware test complete.")


if __name__ == "__main__":
    main()
