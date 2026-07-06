#!/usr/bin/env python3
"""
Developer demo for capturing a snapshot with the Betabox Vision subsystem.
"""

from time import sleep

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.vision import Vision


def main() -> None:
    print()
    print("Betabox Vision Snapshot Demo")
    print("============================")
    print()

    with Vision.default(BETABOX_CAR) as vision:
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

    print()
    print("Vision snapshot demo complete.")


if __name__ == "__main__":
    main()
