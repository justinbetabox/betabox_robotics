#!/usr/bin/env python3

from time import sleep

from betabox_robotics.vision import FrameSource, WebRTCStreamer

streamer = WebRTCStreamer()

with FrameSource(fps=10) as source:
    print("\nWebRTC streamer interface test")
    print("=============================")

    streamer.start()
    source.register_consumer(streamer)

    sleep(1.0)

    stats = streamer.statistics()

    print(f"running={stats['running']}")
    print(f"clients={stats['clients']}")
    print(f"frames_received={stats['frames_received']}")
    print(f"has_frame={stats['has_frame']}")

    assert stats["running"] is True
    assert stats["frames_received"] > 0
    assert stats["has_frame"] is True

    source.unregister_consumer(streamer)
    streamer.stop()

print("\nWebRTC streamer interface test complete.")
