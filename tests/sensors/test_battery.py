#!/usr/bin/env python3

from time import sleep

from betabox_car.sensors import Battery

with Battery() as battery:
    print("\nBattery hardware test")
    print("=====================")

    for _ in range(10):
        voltage = battery.voltage()
        status = battery.status()

        print(f"voltage={voltage:.2f} V, status={status}")

        sleep(0.5)

print("\nBattery hardware test complete.")
