#!/usr/bin/env python3
"""
Betabox Ultrasonic sensor developer demo.

Reads distance measurements through the Ultrasonic subsystem using the
configured trigger and echo pins.

This demo validates:

- Ultrasonic.default();
- configured timeout behavior;
- typed distance-reading errors;
- repeated sampling;
- UltrasonicReading status objects;
- compatibility read() return values;
- context-managed cleanup.

The reported distance is measured in centimeters.
"""

from __future__ import annotations

from time import sleep

from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import (
    Ultrasonic,
    UltrasonicError,
    UltrasonicReadError,
    UltrasonicTimeoutError,
)

READING_COUNT = 10
READING_DELAY = 0.3
SAMPLES_PER_READING = 10


def print_configuration(
    sensor: Ultrasonic,
) -> None:
    print()
    print("Configuration")
    print("-------------")
    print(f"Trigger pin: GPIO{sensor.trigger_pin.pin_number}")
    print(f"Echo pin:    GPIO{sensor.echo_pin.pin_number}")
    print(f"Timeout:     {sensor.timeout:.4f} seconds")
    print(f"Samples:     {SAMPLES_PER_READING}")
    print(f"Closed:      {sensor.closed}")


def print_distance_readings(
    sensor: Ultrasonic,
) -> None:
    print()
    print("Distance readings")
    print("-----------------")

    for reading_number in range(
        1,
        READING_COUNT + 1,
    ):
        try:
            reading = sensor.reading(
                samples=SAMPLES_PER_READING,
            )

            print(
                f"{reading_number:>2}: "
                f"{reading.distance_cm:>7.2f} cm "
                f"({reading.samples_requested} "
                f"samples requested)"
            )

        except UltrasonicTimeoutError as exc:
            print(f"{reading_number:>2}: timeout — {exc}")

        except UltrasonicReadError as exc:
            print(f"{reading_number:>2}: invalid pulse — {exc}")

        if reading_number < READING_COUNT:
            sleep(READING_DELAY)


def print_compatibility_reading(
    sensor: Ultrasonic,
) -> None:
    print()
    print("Compatibility API")
    print("-----------------")

    value = sensor.read(
        times=SAMPLES_PER_READING,
    )

    if value == -1:
        print("read() returned -1: ultrasonic timeout")
    elif value == -2:
        print("read() returned -2: invalid ultrasonic pulse")
    else:
        print(f"read() returned {value:.2f} cm")


def main() -> int:
    print()
    print("Betabox Ultrasonic demo")
    print("=======================")
    print()
    print(
        "Place a solid object in front of the ultrasonic sensor "
        "and move it closer or farther away while readings are taken."
    )
    print("Press Ctrl+C at any time to stop the demo.")

    cleanup_sensor: Ultrasonic | None = None

    try:
        sensor = Ultrasonic.default(
            BETABOX_CAR.sensors.ultrasonic,
        )
        cleanup_sensor = sensor

        with sensor:
            print_configuration(sensor)

            print_distance_readings(sensor)

            print_compatibility_reading(sensor)

        print()
        print(f"Closed after context exit: {sensor.closed}")

    except KeyboardInterrupt:
        print()
        print("Ultrasonic demo interrupted.")
        return 130

    except UltrasonicError as exc:
        print()
        print(f"Ultrasonic demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Ultrasonic demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_sensor is not None and not cleanup_sensor.closed:
            cleanup_sensor.close()

    print()
    print("Ultrasonic demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
