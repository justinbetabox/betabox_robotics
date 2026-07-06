#!/usr/bin/env python3

import tempfile

import numpy as np

from betabox_robotics.vision import Frame, SnapshotService


class FakeFrameSource:
    def __init__(self):
        self.frame = Frame.create(np.zeros((100, 100, 3), dtype=np.uint8))

    def latest_frame(self):
        return self.frame


def test_snapshot_service_saves_image():
    frame_source = FakeFrameSource()

    with tempfile.TemporaryDirectory() as temp_dir:
        service = SnapshotService(frame_source, directory=temp_dir)

        snapshot = service.capture(filename="test_snapshot.jpg")

        print("\nSnapshot hardware-independent test")
        print("==================================")
        print(f"exists={snapshot.path.exists()}")
        print(f"filename={snapshot.path.name}")
        print(f"format={snapshot.format}")
        print(f"timestamp={snapshot.timestamp}")

        assert snapshot.path.exists()
        assert snapshot.path.suffix == ".jpg"
        assert snapshot.format == "jpg"
        assert snapshot.timestamp == frame_source.frame.timestamp

    print("\nSnapshot test complete.")


if __name__ == "__main__":
    test_snapshot_service_saves_image()
