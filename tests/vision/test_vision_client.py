from __future__ import annotations

from time import sleep

from betabox_robotics.vision import (
    ClientMetadata,
    ClientVisionStatistics,
    VisionClient,
)


def main() -> None:
    print()
    print("Betabox VisionClient Test")
    print("=========================")
    print()

    client = VisionClient()

    stats = client.statistics()
    print("Stats:")
    print(stats)

    assert isinstance(stats, ClientVisionStatistics)
    assert stats.running is True
    assert stats.camera.running is True
    assert stats.camera.has_frame is True
    assert stats.streaming.running is True

    snapshot = client.snapshot()
    print("Snapshot:", snapshot)
    assert snapshot.path.exists()

    path = client.start_recording()
    print("Recording started:", path)

    sleep(3)

    recording = client.stop_recording()
    print("Recording stopped:", recording)
    assert recording.path.exists()
    assert recording.frame_count > 0

    metadata = client.metadata()
    print("Metadata:")
    print(metadata)

    assert metadata is None or isinstance(metadata, ClientMetadata)

    print()
    print("VisionClient test passed.")
    print()


if __name__ == "__main__":
    main()
