#!/usr/bin/env python3
"""
Developer demo for the Betabox PWM hardware abstraction.
"""

from time import sleep

from betabox_car.hardware import PWM, Pins


def main() -> None:
    print()
    print("Betabox PWM Demo")
    print("================")
    print()

    with PWM(Pins.P0) as pwm:
        print("Setting frequency to 50 Hz...")
        pwm.set_frequency(50)

        print("Setting duty cycle to 50%...")
        pwm.set_duty_cycle(50)
        sleep(1)

        print("Setting duty cycle to 25%...")
        pwm.set_duty_cycle(25)
        sleep(1)

        print("Setting duty cycle to 75%...")
        pwm.set_duty_cycle(75)
        sleep(1)

        print("Turning PWM off...")
        pwm.off()

    print()
    print("PWM demo complete.")


if __name__ == "__main__":
    main()
