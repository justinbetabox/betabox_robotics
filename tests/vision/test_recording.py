#!/usr/bin/env python3

import tempfile

import numpy as np

from betabox_robotics.vision import Frame, RecordingService


def test_recording_service_writes_video():
    with tempfile.TemporaryDirectory() as temp_dir:
        service = RecordingService(directory=temp_dir, fps=10)
        path = service.start(filename="test_recording.mp4")

        for _ in range(10):
            frame = Frame.create(np.zeros((100, 100, 3), dtype=np.uint8))
            service.on_frame(frame)

        recording = service.stop()

        print("\nRecording hardware-independent test")
        print("===================================")
        print(f"path={recording.path}")
        print(f"exists={recording.path.exists()}")
        print(f"frame_count={recording.frame_count}")
        print(f"duration={recording.duration}")
        print(f"fps={recording.fps}")

        assert path.exists()
        assert recording.path.exists()
        assert recording.path.suffix == ".mp4"
        assert recording.frame_count == 10
        assert recording.fps == 10

    print("\nRecording test complete.")


if __name__ == "__main__":
    test_recording_service_writes_video()
