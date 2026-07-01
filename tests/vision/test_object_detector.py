#!/usr/bin/env python3

import numpy as np

from betabox_car.vision import Frame, ModelDetection, ObjectDetector


class FakeObjectDetectionRuntime:
    def __init__(self) -> None:
        self.frames_seen = 0

    def detect(self, frame: Frame) -> list[ModelDetection]:
        self.frames_seen += 1

        return [
            ModelDetection(
                label="person",
                confidence=0.98,
                box=(10, 20, 100, 200),
                data={"class_id": 1},
            ),
            ModelDetection(
                label="chair",
                confidence=0.85,
                box=(150, 50, 60, 90),
                data={"class_id": 62},
            ),
            ModelDetection(
                label="low_confidence",
                confidence=0.25,
                box=(1, 2, 3, 4),
                data={"class_id": 999},
            ),
        ]


def test_object_detector_converts_runtime_results_to_metadata():
    runtime = FakeObjectDetectionRuntime()
    detector = ObjectDetector(runtime=runtime, enabled=True, min_confidence=0.5)

    frame = Frame.create(np.zeros((240, 320, 3), dtype=np.uint8))
    metadata = detector.detect(frame)

    print("\nObject detector hardware-independent test")
    print("=========================================")
    print(f"source={metadata.source}")
    print(f"count={metadata.data.get('count')}")
    print(f"min_confidence={metadata.data.get('min_confidence')}")
    print(f"runtime_frames_seen={runtime.frames_seen}")
    print(f"detection_count={len(metadata.detections)}")

    assert metadata.source == "objects"
    assert metadata.data["count"] == 2
    assert metadata.data["min_confidence"] == 0.5
    assert runtime.frames_seen == 1
    assert len(metadata.detections) == 2

    first = metadata.detections[0]
    second = metadata.detections[1]

    print(f"first_label={first.label}")
    print(f"first_confidence={first.confidence}")
    print(f"first_box={first.box}")
    print(f"first_center={first.center}")

    assert first.label == "person"
    assert first.confidence == 0.98
    assert first.box == (10, 20, 100, 200)
    assert first.center == (60, 120)
    assert first.data["class_id"] == 1

    assert second.label == "chair"
    assert second.confidence == 0.85
    assert second.box == (150, 50, 60, 90)
    assert second.center == (180, 95)
    assert second.data["class_id"] == 62

    print("\nObject detector test complete.")


def test_object_detector_reports_missing_runtime():
    detector = ObjectDetector(enabled=True)

    frame = Frame.create(np.zeros((100, 100, 3), dtype=np.uint8))
    metadata = detector.detect(frame)

    print("\nObject detector missing-runtime test")
    print("====================================")
    print(f"source={metadata.source}")
    print(f"count={metadata.data.get('count')}")
    print(f"error={metadata.data.get('error')}")

    assert metadata.source == "objects"
    assert metadata.data["count"] == 0
    assert "runtime" in metadata.data["error"]


def test_object_detector_can_be_configured_on_enable():
    runtime = FakeObjectDetectionRuntime()
    detector = ObjectDetector()

    detector.enable(runtime=runtime, min_confidence=0.75)

    print("\nObject detector configuration test")
    print("==================================")
    print(f"enabled={detector.enabled}")
    print(f"min_confidence={detector.min_confidence}")
    print(f"has_runtime={detector.runtime is runtime}")

    assert detector.enabled is True
    assert detector.runtime is runtime
    assert detector.min_confidence == 0.75


if __name__ == "__main__":
    test_object_detector_converts_runtime_results_to_metadata()
    test_object_detector_reports_missing_runtime()
    test_object_detector_can_be_configured_on_enable()

    print("\nObject detector tests complete.")
