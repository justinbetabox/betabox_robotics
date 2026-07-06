#!/usr/bin/env python3

from betabox_robotics.vision import WebRTCSignalingServer, WebRTCStreamer


def test_signaling_server_can_be_created():
    streamer = WebRTCStreamer(fps=20)
    server = WebRTCSignalingServer(streamer, host="0.0.0.0", port=8080)

    print("\nWebRTC signaling server test")
    print("============================")
    print(f"host={server.host}")
    print(f"port={server.port}")
    print(f"streamer={type(server.streamer).__name__}")

    assert server.host == "0.0.0.0"
    assert server.port == 8080
    assert server.streamer is streamer

    print("\nWebRTC signaling server test complete.")


if __name__ == "__main__":
    test_signaling_server_can_be_created()
