#!/usr/bin/env python3
"""
Developer demo for color detection in the Betabox Vision pipeline.

This example starts the Vision frame pipeline, registers a ColorDetector,
and prints metadata produced by the detector. It does not draw overlays
or depend on streaming.
"""

from time import sleep

from betabox_car.vision import Vision


def main() -> None:
    vision = Vision()

    vision.detection.color.enable(
        ["red", "green", "blue"],
        min_area=500,
    )

    try:
        print()
        print("Betabox Vision Color Detection Demo")
        print("===================================")
        print()
        print("Starting Vision...")
        vision.start()
        print("Looking for red, green, and blue objects.")
        print("Press Ctrl+C to stop.")
        print()

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

            sleep(1)

    except KeyboardInterrupt:
        print()
        print("Stopping...")

    finally:
        vision.stop()


if __name__ == "__main__":
    main()
