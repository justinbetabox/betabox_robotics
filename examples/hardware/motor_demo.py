#!/usr/bin/env python3
"""
Betabox motor developer demo.

Exercises the configured left and right drive motors using the low-level
Motor, PWM, and Pin hardware APIs.

This demo validates:

- configured motor wiring;
- forward and backward movement;
- controlled speed ramping;
- normal ramped stops;
- immediate emergency stops;
- safe direction changes;
- independent and combined motor control;
- context-managed cleanup.

WARNING:
This demo moves the robot. Raise the wheels off the ground or place the
robot in a clear test area before running it.
"""

from __future__ import annotations

from contextlib import ExitStack
from time import sleep

from betabox_robotics.hardware import (
    PWM,
    HardwareError,
    Motor,
    MotorError,
    Pin,
)
from betabox_robotics.robots import BETABOX_CAR

TEST_SPEED = 30.0
MOVE_DURATION = 1.0
PAUSE_DURATION = 0.5

RAMP_SPEEDS = (
    0.0,
    10.0,
    20.0,
    30.0,
    40.0,
    50.0,
)


def print_motor_state(
    label: str,
    motor: Motor,
) -> None:
    print(
        f"{label:<24}"
        f"speed={motor.get_speed():>6.1f}% "
        f"reversed={motor.reversed} "
        f"closed={motor.closed}"
    )


def pause(
    seconds: float = PAUSE_DURATION,
) -> None:
    sleep(seconds)


def run_single_motor_demo(
    name: str,
    motor: Motor,
) -> None:
    print()
    print(f"{name} motor")
    print("-" * (len(name) + 6))

    print("Forward with controlled ramp...")
    motor.forward(TEST_SPEED)
    print_motor_state(
        "After forward",
        motor,
    )
    sleep(MOVE_DURATION)

    print("Normal stop with controlled ramp...")
    motor.stop()
    print_motor_state(
        "After stop",
        motor,
    )
    pause()

    print("Backward with controlled ramp...")
    motor.backward(TEST_SPEED)
    print_motor_state(
        "After backward",
        motor,
    )
    sleep(MOVE_DURATION)

    print("Normal stop with controlled ramp...")
    motor.stop()
    print_motor_state(
        "After stop",
        motor,
    )
    pause()

    print("Starting forward for emergency-stop test...")
    motor.forward(TEST_SPEED)
    print_motor_state(
        "Before emergency stop",
        motor,
    )
    sleep(MOVE_DURATION)

    print("Emergency stop...")
    motor.emergency_stop()
    print_motor_state(
        "After emergency stop",
        motor,
    )
    pause()


def run_both_motor_demo(
    left: Motor,
    right: Motor,
) -> None:
    print()
    print("Combined motor operations")
    print("-------------------------")

    print("Both motors forward...")
    left.forward(TEST_SPEED)
    right.forward(TEST_SPEED)

    print_motor_state(
        "Left",
        left,
    )
    print_motor_state(
        "Right",
        right,
    )

    sleep(MOVE_DURATION)

    print("Controlled stop...")
    left.stop()
    right.stop()
    pause()

    print("Both motors backward...")
    left.backward(TEST_SPEED)
    right.backward(TEST_SPEED)

    print_motor_state(
        "Left",
        left,
    )
    print_motor_state(
        "Right",
        right,
    )

    sleep(MOVE_DURATION)

    print("Controlled stop...")
    left.stop()
    right.stop()
    pause()


def run_counter_rotation_demo(
    left: Motor,
    right: Motor,
) -> None:
    print()
    print("Counter-rotation operations")
    print("---------------------------")

    print("Left forward, right backward...")
    left.forward(TEST_SPEED)
    right.backward(TEST_SPEED)
    sleep(MOVE_DURATION)

    left.stop()
    right.stop()
    pause()

    print("Left backward, right forward...")
    left.backward(TEST_SPEED)
    right.forward(TEST_SPEED)
    sleep(MOVE_DURATION)

    left.stop()
    right.stop()
    pause()


def run_ramp_demo(
    left: Motor,
    right: Motor,
) -> None:
    print()
    print("Explicit speed ramp")
    print("-------------------")
    print(
        "This section uses immediate speed commands to show each "
        "requested level. Normal Motor.forward() commands already "
        "perform their own internal smoothing."
    )

    for speed in RAMP_SPEEDS:
        print(f"Setting both motors to {speed:.0f}%")

        left.set_speed(
            speed,
            smooth=False,
        )
        right.set_speed(
            speed,
            smooth=False,
        )

        print_motor_state(
            "Left",
            left,
        )
        print_motor_state(
            "Right",
            right,
        )

        sleep(0.4)

    for speed in reversed(RAMP_SPEEDS[:-1]):
        print(f"Setting both motors to {speed:.0f}%")

        left.set_speed(
            speed,
            smooth=False,
        )
        right.set_speed(
            speed,
            smooth=False,
        )

        sleep(0.4)

    left.stop()
    right.stop()


def emergency_stop_both(
    left: Motor | None,
    right: Motor | None,
) -> None:
    for motor in (
        left,
        right,
    ):
        if motor is None or motor.closed:
            continue

        try:
            motor.emergency_stop()
        except (
            HardwareError,
            OSError,
            RuntimeError,
        ):
            pass


def main() -> int:
    left_config = BETABOX_CAR.drive.left_motor
    right_config = BETABOX_CAR.drive.right_motor

    print()
    print("Betabox motor demo")
    print("==================")
    print()
    print("WARNING: This demo moves both drive motors.")
    print(
        "Raise the robot so its wheels cannot contact the floor, "
        "or place it in a large clear test area."
    )
    print()
    print("Press Ctrl+C at any time to trigger an immediate emergency stop.")

    cleanup_left: Motor | None = None
    cleanup_right: Motor | None = None

    try:
        with ExitStack() as stack:
            left = stack.enter_context(
                Motor(
                    PWM(left_config.pwm),
                    Pin(
                        left_config.direction,
                        mode=Pin.OUT,
                    ),
                    reversed=left_config.reversed,
                )
            )
            cleanup_left = left

            right = stack.enter_context(
                Motor(
                    PWM(right_config.pwm),
                    Pin(
                        right_config.direction,
                        mode=Pin.OUT,
                    ),
                    reversed=right_config.reversed,
                )
            )
            cleanup_right = right

            print()
            print("Motors initialized.")

            print_motor_state(
                "Left",
                left,
            )
            print_motor_state(
                "Right",
                right,
            )

            run_single_motor_demo(
                "Left",
                left,
            )

            run_single_motor_demo(
                "Right",
                right,
            )

            run_both_motor_demo(
                left,
                right,
            )

            run_counter_rotation_demo(
                left,
                right,
            )

            run_ramp_demo(
                left,
                right,
            )

            print()
            print("Final controlled stop...")

            left.stop()
            right.stop()

            print_motor_state(
                "Left",
                left,
            )
            print_motor_state(
                "Right",
                right,
            )

    except KeyboardInterrupt:
        print()
        print("Interrupted. Applying immediate emergency stop...")

        emergency_stop_both(
            cleanup_left,
            cleanup_right,
        )

        return 130

    except MotorError as exc:
        print()
        print(f"Motor demo failed: {exc}")

        emergency_stop_both(
            cleanup_left,
            cleanup_right,
        )

        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Motor demo failed: {type(exc).__name__}: {exc}")

        emergency_stop_both(
            cleanup_left,
            cleanup_right,
        )

        return 1

    finally:
        emergency_stop_both(
            cleanup_left,
            cleanup_right,
        )

    print()
    print("Motor demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
