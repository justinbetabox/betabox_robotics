#!/usr/bin/env python3
"""
Betabox servo developer demo.

Exercises the configured steering, camera pan, and camera tilt servos
using the low-level Servo hardware API.

This demo validates:

- configured servo channels and travel limits;
- logical versus physical angles;
- calibration offsets;
- smooth movement;
- center, minimum, and maximum helpers;
- context-managed cleanup.

WARNING:
This demo physically moves the steering and camera servos. Make sure the
mechanisms can move freely and stop the demo immediately if a servo
binds, chatters, or reaches an unsafe position.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from time import sleep

from betabox_robotics.hardware import (
    HardwareError,
    Servo,
    ServoError,
)
from betabox_robotics.robots import BETABOX_CAR

MOVE_DELAY = 1.0


@dataclass(frozen=True, slots=True)
class ServoDemoConfig:
    name: str
    channel: object
    min_angle: float
    max_angle: float
    offset: float = 0.0


def print_servo_state(
    label: str,
    servo: Servo,
) -> None:
    logical = servo.get_angle()
    physical = servo.physical_angle

    logical_text = f"{logical:.1f}°" if logical is not None else "-"

    physical_text = f"{physical:.1f}°" if physical is not None else "-"

    print(
        f"{label:<22}"
        f"logical={logical_text:<8}"
        f"physical={physical_text:<8}"
        f"offset={servo.offset:>6.1f}° "
        f"closed={servo.closed}"
    )


def move_and_report(
    servo: Servo,
    label: str,
    angle: float,
    *,
    smooth: bool = True,
) -> None:
    print(f"{label}: requesting {angle:.1f}° ({'smooth' if smooth else 'immediate'})")

    servo.move_to(
        angle,
        smooth=smooth,
    )

    print_servo_state(
        "Result",
        servo,
    )

    sleep(MOVE_DELAY)


def run_servo_demo(
    config: ServoDemoConfig,
    servo: Servo,
) -> None:
    print()
    print(config.name)
    print("-" * len(config.name))

    print(f"Channel:       {config.channel}")
    print(f"Physical range: {servo.min_angle:.1f}° to {servo.max_angle:.1f}°")
    print(f"Offset:        {servo.offset:.1f}°")
    print(
        f"Logical range: "
        f"{servo.min_angle - servo.offset:.1f}° to "
        f"{servo.max_angle - servo.offset:.1f}°"
    )

    print()
    print("Centering...")
    servo.center()
    print_servo_state(
        "After center",
        servo,
    )
    sleep(MOVE_DELAY)

    logical_minimum = servo.min_angle - servo.offset

    logical_maximum = servo.max_angle - servo.offset

    midpoint = (logical_minimum + logical_maximum) / 2.0

    quarter_low = (logical_minimum + midpoint) / 2.0

    quarter_high = (midpoint + logical_maximum) / 2.0

    move_and_report(
        servo,
        "Move toward minimum",
        quarter_low,
    )

    move_and_report(
        servo,
        "Move toward maximum",
        quarter_high,
    )

    print("Moving to configured physical minimum...")
    servo.min()
    print_servo_state(
        "After min()",
        servo,
    )
    sleep(MOVE_DELAY)

    print("Moving to configured physical maximum...")
    servo.max()
    print_servo_state(
        "After max()",
        servo,
    )
    sleep(MOVE_DELAY)

    move_and_report(
        servo,
        "Immediate midpoint",
        midpoint,
        smooth=False,
    )

    print("Returning to center...")
    servo.center()
    print_servo_state(
        "Final position",
        servo,
    )
    sleep(MOVE_DELAY)


def build_demo_configs() -> tuple[ServoDemoConfig, ...]:
    steering = BETABOX_CAR.drive.steering
    camera_mount = BETABOX_CAR.camera_mount

    return (
        ServoDemoConfig(
            name="Steering servo",
            channel=steering.servo,
            min_angle=steering.min_angle,
            max_angle=steering.max_angle,
        ),
        ServoDemoConfig(
            name="Camera pan servo",
            channel=camera_mount.pan_servo,
            min_angle=camera_mount.pan_min_angle,
            max_angle=camera_mount.pan_max_angle,
        ),
        ServoDemoConfig(
            name="Camera tilt servo",
            channel=camera_mount.tilt_servo,
            min_angle=camera_mount.tilt_min_angle,
            max_angle=camera_mount.tilt_max_angle,
        ),
    )


def main() -> int:
    print()
    print("Betabox servo demo")
    print("==================")
    print()
    print("WARNING: This demo moves the steering, pan, and tilt servos.")
    print(
        "Make sure the mechanisms are unobstructed and stop the demo "
        "if a servo binds or chatters."
    )
    print()
    print("Press Ctrl+C at any time to stop the demo and release the servo resources.")

    try:
        with ExitStack() as stack:
            servos: list[
                tuple[
                    ServoDemoConfig,
                    Servo,
                ]
            ] = []

            for config in build_demo_configs():
                servo = stack.enter_context(
                    Servo(
                        config.channel,
                        min_angle=config.min_angle,
                        max_angle=config.max_angle,
                        offset=config.offset,
                    )
                )

                servos.append(
                    (
                        config,
                        servo,
                    )
                )

            print()
            print(f"Initialized {len(servos)} servos.")

            for config, servo in servos:
                run_servo_demo(
                    config,
                    servo,
                )

            print()
            print("All servos returned to center.")

    except KeyboardInterrupt:
        print()
        print("Servo demo interrupted. Resources are being released.")
        return 130

    except ServoError as exc:
        print()
        print(f"Servo demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Servo demo failed: {type(exc).__name__}: {exc}")
        return 1

    print()
    print("Servo demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
