#!/usr/bin/env python3
"""
Developer demo for the Betabox Vision WebRTC pipeline.

This example shows how to connect the Vision frame pipeline to the
WebRTC signaling server.

It is intended for developers working on the Vision subsystem. Student
and curriculum code should prefer the public Robot API example instead.
"""

from betabox_car.vision import FrameSource, WebRTCSignalingServer, WebRTCStreamer


def main() -> None:
    # Produce camera frames.
    frame_source = FrameSource(fps=20)

    # Consume frames and publish them over WebRTC.
    streamer = WebRTCStreamer(fps=20)

    # Connect the producer to the consumer.
    frame_source.register_consumer(streamer)

    try:
        frame_source.start()
        streamer.start()

        print()
        print("Betabox Vision WebRTC Demo")
        print("==========================")
        print()
        print("Open this URL in a browser:")
        print("    http://<robot-ip>:8080")
        print()
        print("The browser will negotiate a WebRTC connection")
        print("with the robot and display the live camera stream.")
        print()
        print("Press Ctrl+C to stop.")
        print()

        # Start the signaling server. This blocks until interrupted.
        server = WebRTCSignalingServer(streamer, port=8080)
        server.run()

    finally:
        streamer.stop()
        frame_source.unregister_consumer(streamer)
        frame_source.stop()


if __name__ == "__main__":
    main()
