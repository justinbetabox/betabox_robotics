from __future__ import annotations
from time import sleep

from betabox_robotics.vision import VisionClient


def main() -> None:
    print()
    print("Betabox VisionClient Test")
    print("=========================")
    print()

    client = VisionClient()

    stats = client.statistics()
    print("Stats:")
    print(stats)

    assert stats["running"] is True

    snapshot = client.snapshot()
    print("Snapshot:", snapshot)
    assert snapshot.path.exists()

    path = client.start_recording()
    print("Recording started:", path)

    sleep(3)

    recording = client.stop_recording()
    print("Recording stopped:", recording)
    assert recording.path.exists()

    metadata = client.metadata()
    print("Metadata:")
    print(metadata)

    print()
    print("VisionClient test passed.")
    print()


if __name__ == "__main__":
    main()
