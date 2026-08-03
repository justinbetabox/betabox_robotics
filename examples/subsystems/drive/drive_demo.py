#!/usr/bin/env python3
"""
Betabox Drive subsystem developer demo.

Exercises the configured drive motors and steering servo through the
Drive subsystem API.

This demo validates:

- default configured hardware construction;
- steering movement and centering;
- forward and backward driving;
- independent left and right motor speeds;
- controlled stops;
- immediate emergency stops;
- context-managed hardware cleanup.

WARNING:
This demo moves the robot. Raise the wheels off the ground or place the
robot in a large, clear test area before running it.
"""

from __future__ import annotations

from time import sleep

from betabox_robotics.drive import (
    Drive,
    DriveError,
)
from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots import BETABOX_CAR

TEST_SPEED = 30.0
MOVE_DURATION = 1.5
PAUSE_DURATION = 0.5


def pause(
    seconds: float = PAUSE_DURATION,
) -> None:
    sleep(seconds)


def print_status(
    label: str,
    drive: Drive,
) -> None:
    status = drive.status()

    print()
    print(label)
    print("-" * len(label))
    print(f"Closed:          {status.closed}")
    print(f"Left trim:       {status.left_trim:.3f}")
    print(f"Right trim:      {status.right_trim:.3f}")
    print(f"Steering offset: {status.steering_offset:.1f}°")
    print(f"Left speed:      {drive.left_motor.get_speed():.1f}%")
    print(f"Right speed:     {drive.right_motor.get_speed():.1f}%")

    steering_angle = drive.steering.get_angle()
    physical_angle = drive.steering.physical_angle

    print(
        "Steering angle:  "
        + (f"{steering_angle:.1f}°" if steering_angle is not None else "-")
    )

    print(
        "Physical angle:  "
        + (f"{physical_angle:.1f}°" if physical_angle is not None else "-")
    )


def run_steering_demo(
    drive: Drive,
) -> None:
    print()
    print("Steering")
    print("--------")

    print("Centering steering...")
    drive.center()
    print_status(
        "Centered",
        drive,
    )
    pause()

    print("Turning left 20°...")
    drive.left(20)
    print_status(
        "Left",
        drive,
    )
    pause()

    print("Turning right 20°...")
    drive.right(20)
    print_status(
        "Right",
        drive,
    )
    pause()

    print("Returning to center...")
    drive.center()
    pause()


def run_movement_demo(
    drive: Drive,
) -> None:
    print()
    print("Movement")
    print("--------")

    print(f"Driving forward at {TEST_SPEED:.0f}%...")
    drive.forward(TEST_SPEED)
    print_status(
        "Forward",
        drive,
    )
    sleep(MOVE_DURATION)

    print("Performing controlled stop...")
    drive.stop()
    print_status(
        "Stopped",
        drive,
    )
    pause()

    print(f"Driving backward at {TEST_SPEED:.0f}%...")
    drive.backward(TEST_SPEED)
    print_status(
        "Backward",
        drive,
    )
    sleep(MOVE_DURATION)

    print("Performing controlled stop...")
    drive.stop()
    pause()


def run_independent_speed_demo(
    drive: Drive,
) -> None:
    print()
    print("Independent motor speeds")
    print("------------------------")

    print("Left 20%, right 35%...")
    drive.speed(
        20,
        35,
    )
    print_status(
        "Unequal forward speeds",
        drive,
    )
    sleep(MOVE_DURATION)

    drive.stop()
    pause()

    print("Left forward, right backward...")
    drive.speed(
        25,
        -25,
    )
    print_status(
        "Counter rotation",
        drive,
    )
    sleep(MOVE_DURATION)

    drive.stop()
    pause()


def run_emergency_stop_demo(
    drive: Drive,
) -> None:
    print()
    print("Emergency stop")
    print("--------------")

    print(f"Driving forward at {TEST_SPEED:.0f}%...")
    drive.forward(TEST_SPEED)
    sleep(MOVE_DURATION)

    print("Applying immediate emergency stop...")
    drive.emergency_stop()

    print_status(
        "Emergency stopped",
        drive,
    )
    pause()


def main() -> int:
    print()
    print("Betabox Drive demo")
    print("==================")
    print()
    print("WARNING: This demo moves the drive motors and steering servo.")
    print(
        "Raise the wheels off the ground or place the robot "
        "in a large, clear test area."
    )
    print()
    print("Press Ctrl+C at any time to apply an immediate emergency stop.")

    cleanup_drive: Drive | None = None

    try:
        drive = Drive.default(BETABOX_CAR.drive)
        cleanup_drive = drive

        with drive:
            print_status(
                "Initial state",
                drive,
            )

            run_steering_demo(drive)

            run_movement_demo(drive)

            run_independent_speed_demo(drive)

            run_emergency_stop_demo(drive)

            print()
            print("Returning to a safe final state...")

            drive.stop()
            drive.center()

            print_status(
                "Final active state",
                drive,
            )

        print()
        print(f"Closed after context exit: {drive.closed}")

    except KeyboardInterrupt:
        print()
        print("Interrupted. Applying immediate emergency stop...")

        if cleanup_drive is not None and not cleanup_drive.closed:
            try:
                cleanup_drive.emergency_stop()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass

        return 130

    except DriveError as exc:
        print()
        print(f"Drive demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Drive demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_drive is not None and not cleanup_drive.closed:
            try:
                cleanup_drive.emergency_stop()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass

            cleanup_drive.close()

    print()
    print("Drive demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
