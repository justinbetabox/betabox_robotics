#!/usr/bin/env python3

from betabox_car.hardware import I2C

with I2C() as bus:
    addresses = bus.scan()

print("I2C devices found:")

for address in addresses:
    print(f"- 0x{address:02X}")

if not addresses:
    print("No I2C devices found.")
