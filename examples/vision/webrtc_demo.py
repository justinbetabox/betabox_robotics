#!/usr/bin/env python3

from betabox_car.vision import FrameSource, WebRTCSignalingServer, WebRTCStreamer


def main():
    frame_source = FrameSource(fps=20)
    streamer = WebRTCStreamer(fps=20)

    frame_source.register_consumer(streamer)

    try:
        frame_source.start()
        streamer.start()

        print("\nBetabox WebRTC demo")
        print("===================")
        print("Open this URL in a browser:")
        print("http://<robot-ip>:8080")
        print("\nPress Ctrl+C to stop.")

        server = WebRTCSignalingServer(streamer, port=8080)
        server.run()

    finally:
        frame_source.unregister_consumer(streamer)
        streamer.stop()
        frame_source.stop()


if __name__ == "__main__":
    main()
