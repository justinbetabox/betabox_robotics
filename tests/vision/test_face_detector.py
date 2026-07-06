#!/usr/bin/env python3

import numpy as np

from betabox_robotics.vision import FaceDetector, Frame


def test_face_detector_handles_frame_without_faces():
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    frame = Frame.create(image)

    detector = FaceDetector(enabled=True)
    metadata = detector.detect(frame)

    print("\nFace detector hardware-independent test")
    print("=======================================")
    print(f"source={metadata.source}")
    print(f"count={metadata.data.get('count')}")
    print(f"detection_count={len(metadata.detections)}")

    assert metadata.source == "face"
    assert metadata.data["count"] == 0
    assert len(metadata.detections) == 0

    print("\nFace detector test complete.")


def test_face_detector_can_be_configured_on_enable():
    detector = FaceDetector()

    detector.enable(
        scale_factor=1.2,
        min_neighbors=3,
        min_size=(40, 40),
    )

    print("\nFace detector configuration test")
    print("================================")
    print(f"enabled={detector.enabled}")
    print(f"scale_factor={detector.scale_factor}")
    print(f"min_neighbors={detector.min_neighbors}")
    print(f"min_size={detector.min_size}")

    assert detector.enabled is True
    assert detector.scale_factor == 1.2
    assert detector.min_neighbors == 3
    assert detector.min_size == (40, 40)


if __name__ == "__main__":
    test_face_detector_handles_frame_without_faces()
    test_face_detector_can_be_configured_on_enable()

    print("\nFace detector tests complete.")
