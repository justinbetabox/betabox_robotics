#!/usr/bin/env python3

import numpy as np

from betabox_car.vision import ColorDetector, Frame


def test_color_detector_finds_red_region():
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    # Vision frames are RGB.
    image[20:70, 30:80] = [255, 0, 0]

    frame = Frame.create(image)

    detector = ColorDetector("red", min_area=100, enabled=True)
    metadata = detector.detect(frame)

    print("\nColor detector single-color test")
    print("================================")
    print(f"source={metadata.source}")
    print(f"colors={metadata.data.get('colors')}")
    print(f"counts={metadata.data.get('counts')}")
    print(f"count={metadata.data.get('count')}")
    print(f"detection_count={len(metadata.detections)}")

    assert metadata.source == "color:red"
    assert metadata.data["colors"] == ["red"]
    assert metadata.data["counts"]["red"] == 1
    assert metadata.data["count"] == 1
    assert len(metadata.detections) == 1

    detection = metadata.detections[0]

    print(f"label={detection.label}")
    print(f"box={detection.box}")
    print(f"center={detection.center}")
    print(f"area={detection.data.get('area')}")

    assert detection.label == "red"
    assert detection.box is not None
    assert detection.center is not None
    assert detection.data["area"] >= 100


def test_color_detector_finds_multiple_colors():
    image = np.zeros((120, 120, 3), dtype=np.uint8)

    # Vision frames are RGB.
    image[10:50, 10:50] = [255, 0, 0]  # red
    image[60:100, 10:50] = [0, 255, 0]  # green
    image[60:100, 60:100] = [0, 0, 255]  # blue

    frame = Frame.create(image)

    detector = ColorDetector(["red", "green", "blue"], min_area=100, enabled=True)
    metadata = detector.detect(frame)

    print("\nColor detector multi-color test")
    print("===============================")
    print(f"source={metadata.source}")
    print(f"colors={metadata.data.get('colors')}")
    print(f"counts={metadata.data.get('counts')}")
    print(f"count={metadata.data.get('count')}")
    print(f"detection_count={len(metadata.detections)}")

    assert metadata.source == "color"
    assert metadata.data["colors"] == ["red", "green", "blue"]
    assert metadata.data["counts"]["red"] == 1
    assert metadata.data["counts"]["green"] == 1
    assert metadata.data["counts"]["blue"] == 1
    assert metadata.data["count"] == 3
    assert len(metadata.detections) == 3

    labels = {detection.label for detection in metadata.detections}

    assert labels == {"red", "green", "blue"}


def test_color_detector_can_be_reconfigured_on_enable():
    detector = ColorDetector()

    assert detector.name == "color:red"

    detector.enable(["red", "green", "blue"], min_area=100)

    assert detector.enabled is True
    assert detector.name == "color"
    assert detector.colors == ["red", "green", "blue"]
    assert detector.min_area == 100

    print("\nColor detector configuration test")
    print("=================================")
    print(f"name={detector.name}")
    print(f"colors={detector.colors}")
    print(f"min_area={detector.min_area}")
    print(f"enabled={detector.enabled}")


if __name__ == "__main__":
    test_color_detector_finds_red_region()
    test_color_detector_finds_multiple_colors()
    test_color_detector_can_be_reconfigured_on_enable()

    print("\nColor detector tests complete.")
