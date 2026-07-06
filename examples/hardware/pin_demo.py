#!/usr/bin/env python3
"""
Developer demo for the Betabox Pin hardware abstraction.
"""

from time import sleep

from betabox_robotics.hardware import Pin, Pins


def main() -> None:
    print()
    print("Betabox Pin Demo")
    print("================")
    print()

    with Pin(Pins.D0, mode=Pin.OUT) as pin:
        print("Turning pin on...")
        pin.on()
        sleep(1)

        print("Turning pin off...")
        pin.off()
        sleep(1)

        print("Toggling pin...")
        pin.toggle()
        sleep(1)

        print("Turning pin off...")
        pin.off()

    print()
    print("Pin demo complete.")


if __name__ == "__main__":
    main()
