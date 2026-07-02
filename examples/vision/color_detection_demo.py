#!/usr/bin/env python3
"""
Developer demo for color detection in the Betabox Vision subsystem.
"""

from time import sleep

from betabox_car.robots import BETABOX_CAR
from betabox_car.vision import Vision


def main() -> None:
    print()
    print("Betabox Vision Color Detection Demo")
    print("===================================")
    print()

    with Vision.default(BETABOX_CAR) as vision:
        vision.detection.color.enable(
            ["red", "green", "blue"],
            min_area=500,
        )

        print("Starting Vision...")
        vision.start()

        print("Looking for red, green, and blue objects.")
        print("Press Ctrl+C to stop.")
        print()

        try:
            while True:
                metadata = vision.metadata.latest("color")

                if metadata is None:
                    print("No metadata yet.")
                else:
                    counts = metadata.data.get("counts", {})

                    print(f"Detections: {metadata.data.get('count', 0)}")
                    print(f"Counts: {counts}")

                    if metadata.detections:
                        largest = metadata.detections[0]

                        print(f"  Color: {largest.label}")
                        print(f"  Largest box: {largest.box}")
                        print(f"  Center: {largest.center}")
                        print(f"  Area: {largest.data.get('area')}")

                print()
                sleep(1)

        except KeyboardInterrupt:
            print()
            print("Stopping...")

    print()
    print("Vision color detection demo complete.")


if __name__ == "__main__":
    main()
