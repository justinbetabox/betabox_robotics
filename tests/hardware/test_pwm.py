#!/usr/bin/env python3
"""
Betabox PWM hardware test.

Exercises one PWM output.
"""

from time import sleep

from betabox_car.hardware import PWM, Pins


def main() -> None:
    print("\nPWM hardware test")
    print("=================")

    with PWM(Pins.P0) as pwm:
        pwm.set_frequency(50)

        print("25% duty")
        pwm.set_duty_cycle(25)
        sleep(1)

        print("50% duty")
        pwm.set_duty_cycle(50)
        sleep(1)

        print("75% duty")
        pwm.set_duty_cycle(75)
        sleep(1)

        print("Off")
        pwm.off()

    print()
    print("PWM hardware test complete.")


if __name__ == "__main__":
    main()
