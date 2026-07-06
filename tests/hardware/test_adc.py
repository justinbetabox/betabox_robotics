#!/usr/bin/env python3

from time import sleep

from betabox_robotics.hardware import ADC, Pins


def main() -> None:
    channels = [
        Pins.A0,
        Pins.A1,
        Pins.A2,
        Pins.A3,
        Pins.A4,
        Pins.A5,
        Pins.A6,
        Pins.A7,
    ]

    adcs = [ADC(channel) for channel in channels]

    try:
        print("\nADC hardware test")
        print("=================")

        for _ in range(5):
            for channel, adc in zip(channels, adcs):
                value = adc.read()
                voltage = adc.read_voltage()
                print(f"{channel.name}: value={value}, voltage={voltage:.3f}V")

            print("-" * 40)
            sleep(0.5)

    finally:
        for adc in adcs:
            adc.close()

    print("\nADC hardware test complete.")


if __name__ == "__main__":
    main()
