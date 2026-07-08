from __future__ import annotations

from betabox_robotics.vision import VisionService, VisionServiceConfig


def main() -> None:
    print()
    print("Betabox VisionService Test")
    print("==========================")
    print()

    service = VisionService(
        VisionServiceConfig(
            host="127.0.0.1",
            port=8081,
            fps=10,
        )
    )

    print("Constructed VisionService")

    stats = service.statistics()
    print("Initial statistics:")
    print(stats)

    assert stats["running"] is False
    assert stats["host"] == "127.0.0.1"
    assert stats["port"] == 8081
    assert stats["fps"] == 10

    assert service.frame_source.consumer_count() >= 3
    assert service.streamer is not None
    assert service.detection is not None
    assert service.recording is not None
    assert service.snapshot is not None
    assert service.metadata_bus is not None

    print("Consumers registered:", service.frame_source.consumer_count())

    service.stop()
    print("Stop before start handled safely")

    print()
    print("VisionService construction test passed.")
    print()


if __name__ == "__main__":
    main()
