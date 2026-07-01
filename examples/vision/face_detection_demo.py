#!/usr/bin/env python3
"""
Developer demo for face detection in the Betabox Vision pipeline.

This example starts the Vision frame pipeline, enables the built-in
FaceDetector, and prints metadata produced by the detector. It does not
draw overlays or depend on streaming.
"""

from time import sleep

from betabox_car.vision import Vision


def main() -> None:
    vision = Vision()

    vision.detection.face.enable()

    try:
        print()
        print("Betabox Vision Face Detection Demo")
        print("=================================")
        print()
        print("Starting Vision...")
        vision.start()
        print("Looking for faces.")
        print("Press Ctrl+C to stop.")
        print()

        while True:
            metadata = vision.metadata.latest("face")

            if metadata is None:
                print("No metadata yet.")
            else:
                print(f"Detections: {metadata.data.get('count', 0)}")

                for i, detection in enumerate(metadata.detections, start=1):
                    print(f"Face {i}")
                    print(f"  Box: {detection.box}")
                    print(f"  Center: {detection.center}")
                    print(
                        f"  Size: "
                        f"{detection.data.get('width')} x "
                        f"{detection.data.get('height')}"
                    )

            sleep(1)

    except KeyboardInterrupt:
        print()
        print("Stopping...")

    finally:
        vision.stop()


if __name__ == "__main__":
    main()
