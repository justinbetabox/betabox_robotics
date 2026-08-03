#!/usr/bin/env python3
"""
Betabox I²C bus scan developer demo.

Scans the configured I²C bus and reports connected device addresses.

This demo validates:

- opening the Linux I²C bus;
- running the Betabox I2C.scan() helper;
- parsing normal and kernel-claimed addresses;
- context-managed bus cleanup;
- closed-state handling.

It does not communicate with any detected device beyond the bus scan.
"""

from __future__ import annotations

from betabox_robotics.hardware import (
    I2C,
    HardwareError,
    I2CError,
)

BUS_NUMBER = 1


def print_devices(
    devices: list[int],
) -> None:
    print()
    print("Detected devices")
    print("----------------")

    if not devices:
        print("No I²C devices detected.")
        return

    for address in devices:
        print(f"0x{address:02X}  ({address})")


def main() -> int:
    print()
    print("Betabox I²C scan demo")
    print("=====================")
    print()
    print(f"Bus: /dev/i2c-{BUS_NUMBER}")
    print(
        "This demo scans the bus only. "
        "It does not write configuration data to detected devices."
    )

    cleanup_bus: I2C | None = None

    try:
        bus = I2C(
            bus=BUS_NUMBER,
        )
        cleanup_bus = bus

        print()
        print("I²C bus opened successfully.")
        print(f"Closed: {bus.closed}")

        with bus:
            devices = bus.scan()

            print_devices(devices)

            print()
            print(f"Bus open inside context: {not bus.closed}")

        print()
        print(f"Bus closed after context exit: {bus.closed}")

    except I2CError as exc:
        print()
        print(f"I²C scan failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print()
        print(f"I²C demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_bus is not None and not cleanup_bus.closed:
            cleanup_bus.close()

    print()
    print("I²C scan demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
