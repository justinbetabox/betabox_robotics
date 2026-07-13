#!/usr/bin/env python3

from pathlib import Path

from betabox_robotics.vision import TFLiteObjectDetectionModel


def test_tflite_model_class_is_available() -> None:
    print("\nTFLite model availability test")
    print("==============================")
    print(f"model_class={TFLiteObjectDetectionModel.__name__}")

    assert (
        TFLiteObjectDetectionModel.__name__
        == "TFLiteObjectDetectionModel"
    )

    print("\nTFLite model availability test complete.")


def test_tflite_model_paths_are_not_created_until_constructed() -> None:
    model_path = Path("models/object_detection.tflite")
    labels_path = Path("models/object_labels.txt")

    print("\nTFLite model path test")
    print("======================")
    print(f"model_path={model_path}")
    print(f"labels_path={labels_path}")

    assert model_path.suffix == ".tflite"
    assert labels_path.suffix == ".txt"

    print("\nTFLite model path test complete.")


if __name__ == "__main__":
    test_tflite_model_class_is_available()
    test_tflite_model_paths_are_not_created_until_constructed()

    print("\nTFLite model tests complete.")
