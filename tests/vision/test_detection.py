#!/usr/bin/env python3

import numpy as np

from betabox_car.vision import (
    Detection,
    DetectionManager,
    Detector,
    Frame,
    Metadata,
    MetadataBus,
)


class FakeDetector(Detector):
    def __init__(self) -> None:
        super().__init__("fake", enabled=False)
        self.frames_seen = 0

    def detect(self, frame: Frame) -> Metadata:
        self.frames_seen += 1

        return Metadata.create(
            "fake",
            detections=[
                Detection(
                    label="test",
                    confidence=1.0,
                    box=(10, 20, 30, 40),
                    center=(25, 40),
                )
            ],
            data={"frame_timestamp": frame.timestamp},
        )


def test_detection_manager_publishes_metadata():
    metadata_bus = MetadataBus()
    manager = DetectionManager(metadata_bus)
    detector = FakeDetector()

    manager.register(detector)

    frame = Frame.create(np.zeros((100, 100, 3), dtype=np.uint8))

    manager.on_frame(frame)
    assert metadata_bus.latest("fake") is None
    assert detector.frames_seen == 0

    manager.enable("fake")
    manager.on_frame(frame)

    metadata = metadata_bus.latest("fake")

    print("\nDetection hardware-independent test")
    print("===================================")
    print(f"detectors={manager.names()}")
    print(f"enabled={manager.is_enabled('fake')}")
    print(f"frames_seen={detector.frames_seen}")
    print(f"latest_source={metadata.source if metadata else None}")
    print(f"detection_count={len(metadata.detections) if metadata else 0}")

    assert metadata is not None
    assert metadata.source == "fake"
    assert len(metadata.detections) == 1
    assert metadata.detections[0].label == "test"
    assert detector.frames_seen == 1

    manager.disable("fake")
    manager.on_frame(frame)

    assert detector.frames_seen == 1

    print("\nDetection test complete.")


if __name__ == "__main__":
    test_detection_manager_publishes_metadata()
