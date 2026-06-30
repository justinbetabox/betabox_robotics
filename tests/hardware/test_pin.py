#!/usr/bin/env python3
"""
Betabox Pin Hardware Test

Toggles a digital output pin.
"""

from time import sleep

from betabox_car.hardware import Pin, Pins

print("Pin hardware test")
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
