from types import SimpleNamespace

from betabox_robotics.vision import (
    WebRTCSignalingServer,
    WebRTCStreamer,
)


def test_signaling_server_can_be_created() -> None:
    streamer = WebRTCStreamer()
    vision = SimpleNamespace(streamer=streamer)

    server = WebRTCSignalingServer(
        vision,
        host="0.0.0.0",
        port=8080,
    )

    assert server.host == "0.0.0.0"
    assert server.port == 8080
    assert server.streamer is streamer


if __name__ == "__main__":
    test_signaling_server_can_be_created()
    print("WebRTC signaling tests passed")
