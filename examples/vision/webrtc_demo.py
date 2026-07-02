#!/usr/bin/env python3
"""
Developer demo for the Betabox Vision WebRTC pipeline.

This example connects a FrameSource to a WebRTCStreamer and publishes
live camera frames through the WebRTC signaling server.

It demonstrates the lower-level Vision streaming pipeline rather than
the public Vision subsystem.
"""

from betabox_car.vision import FrameSource, WebRTCSignalingServer, WebRTCStreamer


def main() -> None:
    print()
    print("Betabox Vision WebRTC Demo")
    print("==========================")
    print()

    # Produce camera frames.
    frame_source = FrameSource(fps=20)

    # Consume frames and publish them over WebRTC.
    streamer = WebRTCStreamer(fps=20)

    # Connect the producer to the consumer.
    frame_source.register_consumer(streamer)

    try:
        frame_source.start()
        streamer.start()

        print("Open this URL in a browser:")
        print("    http://<robot-ip>:8080")
        print()
        print("The browser will negotiate a WebRTC connection")
        print("with the robot and display the live camera stream.")
        print()
        print("Press Ctrl+C to stop.")
        print()

        server = WebRTCSignalingServer(streamer, port=8080)
        server.run()

    except KeyboardInterrupt:
        print()
        print("Stopping...")

    finally:
        streamer.stop()
        frame_source.unregister_consumer(streamer)
        frame_source.stop()

    print()
    print("Vision WebRTC demo complete.")


if __name__ == "__main__":
    main()
