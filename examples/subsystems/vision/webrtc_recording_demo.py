#!/usr/bin/env python3
"""
Developer validation demo for running WebRTC streaming and recording
from the same Vision frame pipeline.

This verifies that one camera owner can support multiple simultaneous
Vision consumers.
"""

import threading
from time import sleep

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.vision import Vision, WebRTCSignalingServer, WebRTCStreamer


def main() -> None:
    print()
    print("Betabox Vision WebRTC + Recording Demo")
    print("======================================")
    print()

    with Vision.default(BETABOX_CAR) as vision:
        streamer = WebRTCStreamer(fps=20)
        vision.register_consumer(streamer)

        server = WebRTCSignalingServer(streamer, port=8080)
        server_thread = threading.Thread(
            target=lambda: server.run(handle_signals=False),
            name="BetaboxWebRTCSignaling",
            daemon=True,
        )

        try:
            print("Starting Vision...")
            vision.start()

            print("Starting WebRTC streamer...")
            streamer.start()

            print("Starting signaling server...")
            server_thread.start()

            print()
            print("Open this URL in a browser:")
            print("    http://<robot-ip>:8080")
            print()

            print("Starting recording in 5 seconds...")
            sleep(5)

            print("Recording for 5 seconds...")
            vision.recording.start()
            sleep(5)

            print("Stopping recording...")
            recording = vision.recording.stop()

            print()
            print("Recording saved while WebRTC was running.")
            print(f"Path: {recording.path}")
            print(f"Frames: {recording.frame_count}")
            print(f"Duration: {recording.duration:.2f} seconds")
            print()
            print("Press Ctrl+C to stop the WebRTC demo.")

            while True:
                sleep(1)

        except KeyboardInterrupt:
            print()
            print("Stopping...")

        finally:
            if vision.recording.is_recording():
                vision.recording.stop()

            vision.unregister_consumer(streamer)
            streamer.stop()

    print()
    print("Vision WebRTC + recording demo complete.")


if __name__ == "__main__":
    main()
