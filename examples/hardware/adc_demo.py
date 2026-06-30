#!/usr/bin/env python3

from time import sleep

from betabox_car.hardware import ADC, Pins

with ADC(Pins.A0) as adc:
    while True:
        value = adc.read()
        voltage = adc.read_voltage()

        print(f"value={value}, voltage={voltage:.3f}V")

        sleep(0.5)
