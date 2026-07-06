#!/usr/bin/env python3
"""
Developer demo for the Betabox I2C hardware abstraction.
"""

from betabox_robotics.hardware import I2C


def main() -> None:
    print()
    print("Betabox I2C Demo")
    print("================")
    print()

    with I2C() as bus:
        addresses = bus.scan()

    if addresses:
        print("I2C devices found:")
        for address in addresses:
            print(f"  - 0x{address:02X}")
    else:
        print("No I2C devices found.")

    print()
    print("I2C demo complete.")


if __name__ == "__main__":
    main()
