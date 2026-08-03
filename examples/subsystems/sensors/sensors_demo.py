#!/usr/bin/env python3
"""
Betabox Sensors subsystem developer demo.

Demonstrates the combined Sensors subsystem without duplicating the
full battery, grayscale, and ultrasonic demos.

This demo validates:

- Sensors.default();
- access to the battery, grayscale, and ultrasonic components;
- one structured reading from each sensor;
- combined subsystem status reporting;
- subsystem ownership and context-managed cleanup.

For extended testing of an individual sensor, use its dedicated demo.
"""

from __future__ import annotations

from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import (
    BatteryError,
    GrayscaleError,
    Sensors,
    SensorsError,
    SensorsStatus,
    UltrasonicReadError,
    UltrasonicTimeoutError,
)

ULTRASONIC_SAMPLES = 10
GRAYSCALE_THRESHOLD = 0.5


def print_subsystem_status(
    label: str,
    status: SensorsStatus,
) -> None:
    print()
    print(label)
    print("-" * len(label))
    print(f"Ultrasonic closed: {status.ultrasonic_closed}")
    print(f"Grayscale closed:  {status.grayscale_closed}")
    print(f"Battery closed:    {status.battery_closed}")
    print(f"Subsystem closed:  {status.closed}")


def print_battery_reading(
    sensors: Sensors,
) -> None:
    print()
    print("Battery")
    print("-------")

    try:
        reading = sensors.battery.reading()

        print(f"Voltage:  {reading.voltage:.2f} V")
        print(f"State:    {reading.state.value}")
        print(f"Low:      {reading.low}")
        print(f"Critical: {reading.critical}")

    except BatteryError as exc:
        print(f"Reading failed: {exc}")


def print_ultrasonic_reading(
    sensors: Sensors,
) -> None:
    print()
    print("Ultrasonic")
    print("----------")

    try:
        reading = sensors.ultrasonic.reading(
            samples=ULTRASONIC_SAMPLES,
        )

        print(f"Distance: {reading.distance_cm:.2f} cm")
        print(f"Samples:  {reading.samples_requested}")

    except UltrasonicTimeoutError as exc:
        print("Status:   timeout")
        print(f"Details:  {exc}")

    except UltrasonicReadError as exc:
        print("Status:   invalid pulse")
        print(f"Details:  {exc}")


def print_grayscale_reading(
    sensors: Sensors,
) -> None:
    print()
    print("Grayscale")
    print("---------")

    try:
        reading = sensors.grayscale.reading(
            threshold=GRAYSCALE_THRESHOLD,
        )

        print(f"Raw:        {reading.raw}")
        print(f"Status:     {reading.status}")

        if reading.normalized is None:
            print("Normalized: -")
            print("Mode:       reference thresholds")
        else:
            print(
                "Normalized: "
                f"({reading.normalized[0]:.3f}, "
                f"{reading.normalized[1]:.3f}, "
                f"{reading.normalized[2]:.3f})"
            )
            print("Mode:       floor/line calibration")

    except GrayscaleError as exc:
        print(f"Reading failed: {exc}")


def main() -> int:
    print()
    print("Betabox Sensors demo")
    print("====================")
    print()
    print(
        "This demo creates the combined Sensors subsystem and takes "
        "one reading from each configured sensor."
    )
    print(
        "Use the dedicated battery, grayscale, and ultrasonic demos "
        "for longer or more detailed testing."
    )
    print("Press Ctrl+C at any time to stop the demo.")

    cleanup_sensors: Sensors | None = None

    try:
        sensors = Sensors.default(
            BETABOX_CAR.sensors,
        )
        cleanup_sensors = sensors

        with sensors:
            print_subsystem_status(
                "Initial subsystem status",
                sensors.status(),
            )

            print_battery_reading(sensors)

            print_ultrasonic_reading(sensors)

            print_grayscale_reading(sensors)

            print_subsystem_status(
                "Final active subsystem status",
                sensors.status(),
            )

        print_subsystem_status(
            "Status after context exit",
            sensors.status(),
        )

    except KeyboardInterrupt:
        print()
        print("Sensors demo interrupted.")
        return 130

    except SensorsError as exc:
        print()
        print(f"Sensors demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Sensors demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_sensors is not None and not cleanup_sensors.closed:
            cleanup_sensors.close()

    print()
    print("Sensors demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
