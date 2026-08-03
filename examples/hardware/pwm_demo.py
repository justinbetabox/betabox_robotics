#!/usr/bin/env python3
"""
Betabox PWM developer demo.

Exercises one Robot HAT PWM channel using the Betabox PWM API.

This demo validates:

- channel resolution;
- default 50 Hz setup;
- frequency, period, and prescaler reporting;
- duty-cycle output;
- raw pulse-width output;
- off() behavior;
- context-managed cleanup.

WARNING:
A PWM channel may be connected to a servo, motor controller, LED, or
other device. Confirm that the selected channel and output levels are
safe for the connected hardware before running this demo.
"""

from __future__ import annotations

from time import sleep

from betabox_robotics.hardware import (
    PWM,
    HardwareError,
    Pins,
    PWMError,
)

TEST_CHANNEL = Pins.P0
STEP_DELAY = 1.0

DEMO_FREQUENCY = 50.0
DUTY_CYCLES = (
    0.0,
    25.0,
    50.0,
    75.0,
    100.0,
    0.0,
)


def print_status(
    label: str,
    pwm: PWM,
) -> None:
    prescaler = pwm.get_prescaler()
    duty_cycle = pwm.get_duty_cycle()

    print()
    print(label)
    print("-" * len(label))
    print(f"Channel:      P{pwm.channel}")
    print(f"Timer index:  {pwm.timer_index}")
    print(f"Frequency:    {pwm.get_frequency():.6f} Hz")
    print(f"Prescaler:    {prescaler if prescaler is not None else '-'}")
    print(f"Period:       {pwm.get_period()}")
    print(f"Pulse width:  {pwm.get_pulse_width()}")
    print(
        f"Duty cycle:  {duty_cycle:.3f}%"
        if duty_cycle is not None
        else "Duty cycle:  -"
    )
    print(f"Closed:       {pwm.closed}")


def run_duty_cycle_demo(
    pwm: PWM,
) -> None:
    print()
    print("Duty-cycle sweep")
    print("----------------")

    for percent in DUTY_CYCLES:
        print(f"Setting duty cycle to {percent:.0f}%")

        pwm.set_duty_cycle(percent)

        print(f"  pulse={pwm.get_pulse_width()} duty={pwm.get_duty_cycle():.3f}%")

        sleep(STEP_DELAY)


def run_pulse_width_demo(
    pwm: PWM,
) -> None:
    period = pwm.get_period()

    pulse_widths = (
        0,
        period // 4,
        period // 2,
        period,
        0,
    )

    print()
    print("Raw pulse-width sweep")
    print("---------------------")
    print("These values are timer counts, not microseconds.")

    for pulse_width in pulse_widths:
        print(f"Setting pulse width to {pulse_width}/{period}")

        pwm.set_pulse_width(pulse_width)

        duty = pwm.get_duty_cycle()

        print(f"  pulse={pwm.get_pulse_width()} duty={duty:.3f}%")

        sleep(STEP_DELAY)


def main() -> int:
    print()
    print("Betabox PWM demo")
    print("================")
    print()
    print(f"Configured channel: {TEST_CHANNEL.name} (channel {int(TEST_CHANNEL)})")
    print()
    print(
        "WARNING: Confirm this PWM channel is safe to exercise "
        "with duty cycles up to 100%."
    )
    print(
        "Do not use this demo on a steering or camera servo "
        "without changing the sweep to servo-safe pulse widths."
    )

    cleanup_pwm: PWM | None = None

    try:
        pwm = PWM(TEST_CHANNEL)
        cleanup_pwm = pwm

        print_status(
            "Initial state",
            pwm,
        )

        with pwm:
            print()
            print(f"Setting requested frequency to {DEMO_FREQUENCY:.1f} Hz...")

            pwm.set_frequency(DEMO_FREQUENCY)

            print_status(
                "Configured state",
                pwm,
            )

            run_duty_cycle_demo(pwm)

            run_pulse_width_demo(pwm)

            print()
            print("Turning PWM output off...")

            pwm.off()

            print_status(
                "Final active state",
                pwm,
            )

        print()
        print(f"Closed after context exit: {pwm.closed}")

    except PWMError as exc:
        print()
        print(f"PWM demo failed: {exc}")
        return 1

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print(f"PWM demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        if cleanup_pwm is not None and not cleanup_pwm.closed:
            try:
                cleanup_pwm.off()
            except (
                HardwareError,
                OSError,
                RuntimeError,
            ):
                pass

            cleanup_pwm.close()

    print()
    print("PWM demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
