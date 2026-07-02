#!/usr/bin/env python3
"""
Betabox Pin hardware test.

Toggles a digital output pin.
"""

from time import sleep

from betabox_car.hardware import Pin, Pins


def main() -> None:
    print("\nPin hardware test")
    print("=================")

    with Pin(Pins.D0, mode=Pin.OUT) as pin:
        print("ON")
        pin.on()
        sleep(1)

        print("OFF")
        pin.off()
        sleep(1)

        print("TOGGLE")
        pin.toggle()
        sleep(1)

        pin.off()

    print()
    print("Pin hardware test complete.")


if __name__ == "__main__":
    main()
