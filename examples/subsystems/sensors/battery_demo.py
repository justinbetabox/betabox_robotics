#!/usr/bin/env python3
"""
Betabox Battery sensor developer demo.

Reads the robot battery voltage through the Battery subsystem.

This demo validates:

- Battery.default();
- configured ADC scaling;
- voltage readings;
- BatteryState classification;
- structured BatteryReading values;
- is_low() and is_critical() helpers;
- context-managed cleanup.

Battery states:

- OK: voltage is above the configured low threshold
- LOW: voltage is at or below the low threshold
- CRITICAL: voltage is at or below the critical threshold
"""

from __future__ import annotations

from time import sleep

from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.sensors import (
    Battery,
    BatteryError,
    BatteryState,
)

READING_COUNT = 10
READING_DELAY = 0.5


def print_configuration(
    battery: Battery,
) -> None:
    print()
    print("Configuration")
    print("-------------")
    print(f"ADC channel:       {battery.adc.channel}")
    print(f"Scale:             {battery.scale:.3f}")
    print(f"Low threshold:     {battery.low_voltage:.2f} V")
    print(f"Critical threshold:{battery.critical_voltage:.2f} V")
    print(f"Closed:            {battery.closed}")


def state_label(
    state: BatteryState,
) -> str:
    if state is BatteryState.CRITICAL:
        return "CRITICAL"

    if state is BatteryState.LOW:
        return "LOW"

    return "OK"


def print_reading(
    reading_number: int,
    battery: Battery,
) -> None:
    reading = battery.reading()

    print()
    print(f"Reading {reading_number}")
    print("-" * (8 + len(str(reading_number))))
    print(f"Voltage:  {reading.voltage:.2f} V")
    print(f"State:    {state_label(reading.state)}")
    print(f"Low:      {reading.low}")
    print(f"Critical: {reading.critical}")


def main() -> int:
    print()
    print("Betabox Battery demo")
    print("====================")
    print()
    print(
        "This demo reads the battery voltage repeatedly and reports "
        "its configured health state."
    )
    print("Press Ctrl+C at any time to stop the demo.")

    cleanup_battery: Battery | None = None

    try:
        battery = Battery.default(
            BETABOX_CAR.sensors.battery,
        )
        cleanup_battery = battery

        with battery:
            print_configuration(battery)

            for reading_number in range(
                1,
                READING_COUNT + 1,
            ):
                print_reading(
                    reading_number,
                    battery,
                )

                if reading_number < READING_COUNT:
                    sleep(READING_DELAY)

        print()
        print(f"Closed after context exit: {battery.closed}")

    except KeyboardInterrupt:
        print()
        print("Battery demo interrupted.")
        return 130

    except BatteryError as exc:
        print()
        print(f"Battery demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"Battery demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_battery is not None and not cleanup_battery.closed:
            cleanup_battery.close()

    print()
    print("Battery demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
