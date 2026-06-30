#!/usr/bin/env python3
"""
Developer demo for recording video from the Betabox Vision pipeline.

This example uses the Vision subsystem directly. It starts the frame
pipeline, records a short video, saves it to the user's media videos
directory, and then cleans up the camera.
"""

from time import sleep

from betabox_car.vision import Vision


def main() -> None:
    vision = Vision()

    try:
        print()
        print("Betabox Vision Recording Demo")
        print("=============================")
        print()
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

    finally:
        if vision.recording.is_recording():
            vision.recording.stop()

        vision.stop()


if __name__ == "__main__":
    main()
