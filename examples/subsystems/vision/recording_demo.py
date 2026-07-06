#!/usr/bin/env python3
"""
Developer demo for recording video with the Betabox Vision subsystem.
"""

from time import sleep

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.vision import Vision


def main() -> None:
    print()
    print("Betabox Vision Recording Demo")
    print("=============================")
    print()

    with Vision.default(BETABOX_CAR) as vision:
        print("Starting Vision...")
        vision.start()

        # Give the camera pipeline a brief moment to produce frames.
        sleep(1)

        print("Starting recording...")
        vision.recording.start()

        sleep(5)

        print("Stopping recording...")
        recording = vision.recording.stop()

        print()
        print("Recording saved.")
        print(f"Path: {recording.path}")
        print(f"Frames: {recording.frame_count}")
        print(f"Duration: {recording.duration:.2f} seconds")
        print(f"FPS: {recording.fps}")

    print()
    print("Vision recording demo complete.")


if __name__ == "__main__":
    main()
