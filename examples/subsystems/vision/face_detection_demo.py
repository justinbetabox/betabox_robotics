#!/usr/bin/env python3
"""
Developer demo for face detection in the Betabox Vision subsystem.
"""

from time import sleep

from betabox_car.robots import BETABOX_CAR
from betabox_car.vision import Vision


def main() -> None:
    print()
    print("Betabox Vision Face Detection Demo")
    print("==================================")
    print()

    with Vision.default(BETABOX_CAR) as vision:
        vision.detection.face.enable()

        print("Starting Vision...")
        vision.start()

        print("Looking for faces.")
        print("Press Ctrl+C to stop.")
        print()

        try:
            while True:
                metadata = vision.metadata.latest("face")

                if metadata is None:
                    print("No metadata yet.")
                else:
                    print(f"Detections: {metadata.data.get('count', 0)}")

                    for index, detection in enumerate(metadata.detections, start=1):
                        print(f"Face {index}")
                        print(f"  Box: {detection.box}")
                        print(f"  Center: {detection.center}")
                        print(
                            f"  Size: "
                            f"{detection.data.get('width')} x "
                            f"{detection.data.get('height')}"
                        )

                print()
                sleep(1)

        except KeyboardInterrupt:
            print()
            print("Stopping...")

    print()
    print("Vision face detection demo complete.")


if __name__ == "__main__":
    main()
