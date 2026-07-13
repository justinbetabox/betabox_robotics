#!/usr/bin/env python3
"""
Developer validation demo for running WebRTC streaming and recording
from the same managed Vision frame pipeline.

This verifies that one camera owner can support streaming and recording
simultaneously.
"""

import threading
from time import sleep

from betabox_robotics.vision import (
VisionService,
VisionServiceConfig,
)

def main() -> None:
    print()
    print("Betabox Vision WebRTC + Recording Demo")
    print("======================================")
    print()


    config = VisionServiceConfig(
        host="0.0.0.0",
        port=8080,
        fps=20,
    )

    with VisionService(config) as vision:
        server_thread = threading.Thread(
            target=lambda: vision.server.run(
                handle_signals=False,
            ),
            name="BetaboxWebRTCSignaling",
            daemon=True,
        )

        try:
            print("Starting Vision service...")
            server_thread.start()

            print()
            print("Open this URL in a browser:")
            print(f"    http://<robot-ip>:{config.port}")
            print()

            print()
            print("Starting recording in 5 seconds...")
            sleep(5)

            print("Recording for 5 seconds...")
            recording_path = vision.start_recording()

            sleep(5)

            print("Stopping recording...")
            recording = vision.stop_recording()

            print()
            print("Recording saved while WebRTC was running.")
            print(f"Requested path: {recording_path}")
            print(f"Saved path    : {recording.path}")
            print(f"Frames        : {recording.frame_count}")
            print(f"Duration      : {recording.duration:.2f} seconds")
            print()
            print("Press Ctrl+C to stop the WebRTC demo.")

            while True:
                sleep(1)

        except KeyboardInterrupt:
            print()
            print("Stopping...")

        finally:
            if vision.recording.is_recording():
                vision.stop_recording()

    print()
    print("Vision WebRTC + recording demo complete.")


if __name__ == "__main__":
    main()
