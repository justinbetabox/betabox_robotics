#!/usr/bin/env python3
"""
Developer demo for capturing a snapshot from the Betabox Vision pipeline.

This example uses the Vision subsystem directly. It starts the frame
pipeline, captures one still image from the latest frame, and then
cleans up the camera.
"""

from time import sleep

from betabox_car.vision import Vision


def main() -> None:
    vision = Vision()

    try:
        print()
        print("Betabox Vision Snapshot Demo")
        print("============================")
        print()
        print("Starting Vision...")
        vision.start()

        # Give the camera pipeline a brief moment to produce its first frame.
        sleep(1)

        snapshot = vision.snapshot.capture()

        print()
        print("Snapshot captured.")
        print(f"Path: {snapshot.path}")
        print(f"Format: {snapshot.format}")
        print(f"Timestamp: {snapshot.timestamp}")

    finally:
        vision.stop()


if __name__ == "__main__":
    main()
