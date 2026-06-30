#!/usr/bin/env python3

from time import sleep

from betabox_car.hardware import Pin, Pins

with Pin(Pins.D0, mode=Pin.OUT) as pin:
    print("Pin on")
    pin.on()
    sleep(1)

    print("Pin off")
    pin.off()
    sleep(1)

    print("Toggle")
    pin.toggle()
    sleep(1)

    print("Pin off")
    pin.off()

print("Pin demo complete.")
