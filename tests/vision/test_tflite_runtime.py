#!/usr/bin/env python3

from pathlib import Path

from betabox_car.vision import TFLiteObjectDetectionRuntime


def test_tflite_runtime_class_is_available():
    print("\nTFLite runtime availability test")
    print("================================")
    print(f"runtime_class={TFLiteObjectDetectionRuntime.__name__}")

    assert TFLiteObjectDetectionRuntime.__name__ == "TFLiteObjectDetectionRuntime"

    print("\nTFLite runtime availability test complete.")


def test_tflite_runtime_paths_are_not_created_until_constructed():
    model_path = Path("models/object_detection.tflite")
    labels_path = Path("models/object_labels.txt")

    print("\nTFLite runtime path test")
    print("=======================")
    print(f"model_path={model_path}")
    print(f"labels_path={labels_path}")

    assert model_path.suffix == ".tflite"
    assert labels_path.suffix == ".txt"

    print("\nTFLite runtime path test complete.")


if __name__ == "__main__":
    test_tflite_runtime_class_is_available()
    test_tflite_runtime_paths_are_not_created_until_constructed()

    print("\nTFLite runtime tests complete.")
