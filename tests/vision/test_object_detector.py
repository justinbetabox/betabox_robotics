import unittest

from betabox_robotics.vision.detector import DetectorError
from betabox_robotics.vision.detectors.object import (
    ObjectDetector,
    _validate_min_confidence,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.model_runtime import ModelDetection


class FakeObjectDetectionModel:
    def __init__(
        self,
        detections: list[ModelDetection] | None = None,
    ) -> None:
        self.detections = detections if detections is not None else []
        self.frames: list[Frame] = []

    def detect(
        self,
        frame: Frame,
    ) -> list[ModelDetection]:
        self.frames.append(frame)
        return list(self.detections)


class FailingObjectDetectionModel:
    def detect(
        self,
        frame: Frame,
    ) -> list[ModelDetection]:
        raise RuntimeError("model failed")


class InvalidObjectDetectionModel:
    def detect(
        self,
        frame: Frame,
    ) -> list[object]:
        return [
            object(),
        ]


class ObjectDetectorValidationTests(unittest.TestCase):
    def test_validate_min_confidence(self) -> None:
        self.assertEqual(
            _validate_min_confidence(0.5),
            0.5,
        )

    def test_validate_min_confidence_rejects_invalid_type(self) -> None:
        for value in (
            True,
            "0.5",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "min_confidence must be a number",
                ),
            ):
                _validate_min_confidence(value)

    def test_validate_min_confidence_rejects_non_finite_value(self) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "min_confidence must be finite",
                ),
            ):
                _validate_min_confidence(value)

    def test_validate_min_confidence_rejects_out_of_range_value(
        self,
    ) -> None:
        for value in (
            -0.1,
            1.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "min_confidence must be between 0.0 and 1.0",
                ),
            ):
                _validate_min_confidence(value)


class ObjectDetectorTests(unittest.TestCase):
    def test_default_configuration(self) -> None:
        detector = ObjectDetector()

        self.assertEqual(
            detector.name,
            "objects",
        )
        self.assertIsNone(detector.model)
        self.assertEqual(
            detector.min_confidence,
            0.5,
        )
        self.assertFalse(detector.enabled)

    def test_enable_uses_base_detector_state(self) -> None:
        model = FakeObjectDetectionModel()
        detector = ObjectDetector()

        detector.enable(
            model=model,
            min_confidence=0.75,
        )

        self.assertTrue(detector.enabled)
        self.assertIs(
            detector.model,
            model,
        )
        self.assertEqual(
            detector.min_confidence,
            0.75,
        )

    def test_detect_requires_frame(self) -> None:
        detector = ObjectDetector()

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            detector.detect(
                object(),  # type: ignore[arg-type]
            )

    def test_detect_without_model_returns_error_metadata(self) -> None:
        detector = ObjectDetector()
        frame = Frame.create(
            object(),
            timestamp=123.5,
        )

        metadata = detector.detect(frame)

        self.assertEqual(
            metadata.timestamp,
            123.5,
        )
        self.assertEqual(
            metadata.detections,
            (),
        )
        self.assertEqual(
            metadata.data["count"],
            0,
        )
        self.assertEqual(
            metadata.data["error"],
            "object detection model is not configured",
        )

    def test_detect_adapts_model_results(self) -> None:
        model = FakeObjectDetectionModel(
            [
                ModelDetection(
                    label="person",
                    confidence=0.9,
                    box=(
                        10,
                        20,
                        30,
                        40,
                    ),
                    data={
                        "class_id": 1,
                    },
                ),
            ]
        )

        detector = ObjectDetector(
            model=model,
            min_confidence=0.5,
        )

        frame = Frame.create(
            object(),
            timestamp=75.0,
        )

        metadata = detector.detect(frame)

        self.assertEqual(
            model.frames,
            [frame],
        )
        self.assertEqual(
            metadata.timestamp,
            75.0,
        )
        self.assertEqual(
            metadata.data["count"],
            1,
        )
        self.assertEqual(
            metadata.data["min_confidence"],
            0.5,
        )

        detection = metadata.detections[0]

        self.assertEqual(
            detection.label,
            "person",
        )
        self.assertEqual(
            detection.confidence,
            0.9,
        )
        self.assertEqual(
            detection.box,
            (
                10,
                20,
                30,
                40,
            ),
        )
        self.assertEqual(
            detection.center,
            (
                25,
                40,
            ),
        )
        self.assertEqual(
            detection.data,
            {
                "class_id": 1,
            },
        )

    def test_detect_filters_low_confidence_results(self) -> None:
        model = FakeObjectDetectionModel(
            [
                ModelDetection(
                    label="person",
                    confidence=0.4,
                    box=(
                        0,
                        0,
                        10,
                        10,
                    ),
                ),
                ModelDetection(
                    label="car",
                    confidence=0.8,
                    box=(
                        10,
                        10,
                        20,
                        20,
                    ),
                ),
            ]
        )

        detector = ObjectDetector(
            model=model,
            min_confidence=0.5,
        )

        metadata = detector.detect(Frame.create(object()))

        self.assertEqual(
            metadata.data["count"],
            1,
        )
        self.assertEqual(
            metadata.detections[0].label,
            "car",
        )

    def test_model_failure_is_wrapped(self) -> None:
        detector = ObjectDetector(
            model=FailingObjectDetectionModel(),
        )

        with self.assertRaisesRegex(
            DetectorError,
            "object detection failed: model failed",
        ):
            detector.detect(Frame.create(object()))

    def test_invalid_model_result_is_rejected(self) -> None:
        detector = ObjectDetector(
            model=InvalidObjectDetectionModel(),  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(
            DetectorError,
            "object detection model returned an invalid result",
        ):
            detector.detect(Frame.create(object()))


if __name__ == "__main__":
    unittest.main()
