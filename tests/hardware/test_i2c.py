#!/usr/bin/env python3
"""
Betabox I2C Hardware Test

Scans the I2C bus and lists connected devices.
"""

from betabox_car.hardware import I2C

print("I2C hardware test")
print("=================")

with I2C() as bus:
    devices = bus.scan()

if devices:
    print("Detected devices:")

    for address in devices:
        print(f"  0x{address:02X}")
else:
    print("No I2C devices detected.")

print()
print("I2C hardware test complete.")
