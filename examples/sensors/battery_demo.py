#!/usr/bin/env python3

from betabox_car.sensors import Battery

with Battery() as battery:
    voltage = battery.voltage()
    status = battery.status()

    print(f"Battery Voltage : {voltage:.2f} V")
    print(f"Battery Status  : {status}")

    if battery.is_critical():
        print("Battery is critically low.")
    elif battery.is_low():
        print("Battery is low.")
    else:
        print("Battery level is good.")
