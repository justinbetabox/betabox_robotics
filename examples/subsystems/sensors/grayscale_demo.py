#!/usr/bin/env python3
"""
Betabox Grayscale sensor developer demo.

Reads the three-channel grayscale sensor through the Grayscale subsystem.

This demo validates:

- Grayscale.default();
- raw left, middle, and right readings;
- legacy reference-based line/floor status;
- structured GrayscaleReading values;
- configured reference thresholds;
- calibration state reporting;
- context-managed cleanup.

Without floor/line calibration, status values use the configured legacy
reference thresholds:

- 0 means floor
- 1 means line
"""

from __future__ import annotations

from time import sleep

from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import (
    Grayscale,
    GrayscaleError,
)

READING_COUNT = 10
READING_DELAY = 0.3
STATUS_THRESHOLD = 0.5


def print_configuration(
    grayscale: Grayscale,
) -> None:
    floor, line = grayscale.get_calibration()

    print()
    print("Configuration")
    print("-------------")
    print(f"Reference:   {grayscale.reference()}")
    print(f"Floor cal:   {floor if floor is not None else '-'}")
    print(f"Line cal:    {line if line is not None else '-'}")
    print(f"Threshold:   {STATUS_THRESHOLD:.2f}")
    print(f"Closed:      {grayscale.closed}")


def print_reading(
    reading_number: int,
    grayscale: Grayscale,
) -> None:
    reading = grayscale.reading(
        threshold=STATUS_THRESHOLD,
    )

    print()
    print(f"Reading {reading_number}")
    print("-" * (8 + len(str(reading_number))))
    print(f"Raw:         {reading.raw}")
    print(f"Status:      {reading.status}")

    if reading.normalized is None:
        print("Normalized:  -")
        print("Mode:        reference thresholds")
    else:
        print(
            "Normalized:  "
            f"({reading.normalized[0]:.3f}, "
            f"{reading.normalized[1]:.3f}, "
            f"{reading.normalized[2]:.3f})"
        )
        print("Mode:        floor/line calibration")


def main() -> int:
    print()
    print("Betabox Grayscale demo")
    print("======================")
    print()
    print(
        "Move the grayscale sensors over light and dark surfaces "
        "while readings are taken."
    )
    print(
        "Status values are ordered left, middle, right. "
        "A value of 1 indicates line and 0 indicates floor."
    )
    print("Press Ctrl+C at any time to stop the demo.")

    cleanup_grayscale: Grayscale | None = None

    try:
        grayscale = Grayscale.default(
            BETABOX_CAR.sensors.grayscale,
        )
        cleanup_grayscale = grayscale

        with grayscale:
            print_configuration(grayscale)

            for reading_number in range(
                1,
                READING_COUNT + 1,
            ):
                print_reading(
                    reading_number,
                    grayscale,
                )

                if reading_number < READING_COUNT:
                    sleep(READING_DELAY)

        print()
        print(f"Closed after context exit: {grayscale.closed}")

    except KeyboardInterrupt:
        print()
        print("Grayscale demo interrupted.")
        return 130

    except GrayscaleError as exc:
        print()
        print(f"Grayscale demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Grayscale demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_grayscale is not None and not cleanup_grayscale.closed:
            cleanup_grayscale.close()

    print()
    print("Grayscale demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
