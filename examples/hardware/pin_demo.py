#!/usr/bin/env python3
"""
Betabox digital pin developer demo.

Exercises one configured digital output pin using the Betabox Pin API.

This demo validates:

- board pin resolution;
- output mode;
- on/off/high/low helpers;
- toggle behavior;
- value() compatibility API;
- closed-state handling;
- context-managed cleanup.

It does not call close_gpio_factory(). Individual Pin objects release only
their own gpiozero devices. Process-wide GPIO cleanup belongs to the
top-level robot hardware owner.
"""

from __future__ import annotations

from time import sleep

from betabox_robotics.hardware import (
    HardwareError,
    Pin,
    Pins,
)

TEST_PIN = Pins.D0
STEP_DELAY = 1.0


def print_state(
    label: str,
    pin: Pin,
) -> None:
    print(
        f"{label:<18}"
        f"pin={pin.name()} "
        f"mode={pin.mode.value if pin.mode is not None else '-'} "
        f"value={int(pin.device.value)} "
        f"closed={pin.closed}"
    )


def run_output_demo(
    pin: Pin,
) -> None:
    print()
    print("Output operations")
    print("-----------------")

    print_state(
        "Initial",
        pin,
    )

    print("Turning output on...")
    pin.on()
    print_state(
        "After on()",
        pin,
    )
    sleep(STEP_DELAY)

    print("Turning output off...")
    pin.off()
    print_state(
        "After off()",
        pin,
    )
    sleep(STEP_DELAY)

    print("Setting output high...")
    pin.high()
    print_state(
        "After high()",
        pin,
    )
    sleep(STEP_DELAY)

    print("Setting output low...")
    pin.low()
    print_state(
        "After low()",
        pin,
    )
    sleep(STEP_DELAY)

    print("Toggling output...")
    pin.toggle()
    print_state(
        "After toggle()",
        pin,
    )
    sleep(STEP_DELAY)

    print("Writing through value(True)...")
    result = pin.value(True)
    print(f"value(True) returned: {result}")
    print_state(
        "After value()",
        pin,
    )
    sleep(STEP_DELAY)

    print("Writing through call syntax pin(False)...")
    result = pin(False)
    print(f"pin(False) returned: {result}")
    print_state(
        "After __call__",
        pin,
    )


def main() -> int:
    print()
    print("Betabox digital pin demo")
    print("========================")
    print()
    print(f"Configured test pin: {TEST_PIN.name} / GPIO{int(TEST_PIN)}")
    print()
    print(
        "WARNING: Confirm this GPIO is safe to drive as an output "
        "on the connected hardware before continuing."
    )
    print(
        "Do not run this demo while another application owns or "
        "uses the same GPIO line."
    )

    cleanup_pin: Pin | None = None

    try:
        pin = Pin(
            TEST_PIN,
            mode=Pin.OUT,
        )
        cleanup_pin = pin

        print()
        print("Pin opened successfully.")
        print(f"Board name: {pin.board_name or '-'}")
        print(f"GPIO number: {pin.pin_number}")

        with pin:
            run_output_demo(pin)

        print()
        print(f"Closed after context exit: {pin.closed}")

    except (
        HardwareError,
        OSError,
        RuntimeError,
    ) as exc:
        print()
        print(f"Pin demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_pin is not None and not cleanup_pin.closed:
            try:
                cleanup_pin.off()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass

            cleanup_pin.close()

    print()
    print("Digital pin demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
