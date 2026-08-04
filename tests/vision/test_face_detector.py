import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from betabox_robotics.vision.detector import DetectorError
from betabox_robotics.vision.detectors.face import (
    FaceDetector,
    _validate_min_neighbors,
    _validate_min_size,
    _validate_scale_factor,
)
from betabox_robotics.vision.frame import Frame


class FaceValidationTests(unittest.TestCase):
    def test_validate_scale_factor(self) -> None:
        self.assertEqual(
            _validate_scale_factor(1.2),
            1.2,
        )

    def test_validate_scale_factor_rejects_invalid_values(self) -> None:
        for value in (
            True,
            "1.1",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "scale_factor must be a number",
                ),
            ):
                _validate_scale_factor(value)

        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "scale_factor must be finite",
                ),
            ):
                _validate_scale_factor(value)

        for value in (
            1.0,
            0.5,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "scale_factor must be greater than 1.0",
                ),
            ):
                _validate_scale_factor(value)

    def test_validate_min_neighbors(self) -> None:
        self.assertEqual(
            _validate_min_neighbors(5),
            5,
        )

    def test_validate_min_neighbors_rejects_invalid_values(self) -> None:
        for value in (
            True,
            5.0,
            "5",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "min_neighbors must be an integer",
                ),
            ):
                _validate_min_neighbors(value)

        with self.assertRaisesRegex(
            ValueError,
            "min_neighbors cannot be negative",
        ):
            _validate_min_neighbors(-1)

    def test_validate_min_size(self) -> None:
        self.assertEqual(
            _validate_min_size((30, 30)),
            (30, 30),
        )

    def test_validate_min_size_rejects_invalid_shape(self) -> None:
        for value in (
            [30, 30],
            (30,),
            "30x30",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                _validate_min_size(value)

    def test_validate_min_size_rejects_invalid_components(self) -> None:
        for value in (
            (True, 30),
            (30, False),
            (30.0, 30),
            (30, 30.0),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "min_size must contain two integers",
                ),
            ):
                _validate_min_size(value)

        for value in (
            (0, 30),
            (30, 0),
            (-1, 30),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "min_size dimensions must be positive",
                ),
            ):
                _validate_min_size(value)


class FaceDetectorConfigurationTests(unittest.TestCase):
    def _create_detector(
        self,
        *,
        cascade: MagicMock | None = None,
        **kwargs,
    ) -> tuple[FaceDetector, MagicMock]:
        mock_cascade = cascade if cascade is not None else MagicMock()
        mock_cascade.empty.return_value = False

        with patch(
            "betabox_robotics.vision.detectors.face.cv2.CascadeClassifier",
            return_value=mock_cascade,
        ):
            detector = FaceDetector(**kwargs)

        return detector, mock_cascade

    def test_default_configuration(self) -> None:
        detector, _ = self._create_detector()

        self.assertEqual(
            detector.name,
            "face",
        )
        self.assertEqual(
            detector.scale_factor,
            1.1,
        )
        self.assertEqual(
            detector.min_neighbors,
            5,
        )
        self.assertEqual(
            detector.min_size,
            (30, 30),
        )
        self.assertFalse(detector.enabled)

    def test_configure_updates_values(self) -> None:
        detector, _ = self._create_detector()

        detector.configure(
            scale_factor=1.2,
            min_neighbors=7,
            min_size=(40, 50),
        )

        self.assertEqual(
            detector.scale_factor,
            1.2,
        )
        self.assertEqual(
            detector.min_neighbors,
            7,
        )
        self.assertEqual(
            detector.min_size,
            (40, 50),
        )

    def test_enable_configures_and_enables_detector(self) -> None:
        detector, _ = self._create_detector()

        detector.enable(
            scale_factor=1.3,
            min_neighbors=4,
            min_size=(20, 25),
        )

        self.assertTrue(detector.enabled)
        self.assertEqual(
            detector.scale_factor,
            1.3,
        )
        self.assertEqual(
            detector.min_neighbors,
            4,
        )
        self.assertEqual(
            detector.min_size,
            (20, 25),
        )

    def test_empty_cascade_raises(self) -> None:
        cascade = MagicMock()
        cascade.empty.return_value = True

        with (
            patch(
                "betabox_robotics.vision.detectors.face.cv2.CascadeClassifier",
                return_value=cascade,
            ),
            self.assertRaisesRegex(
                DetectorError,
                "failed to load face cascade",
            ),
        ):
            FaceDetector()

    def test_cascade_creation_failure_is_wrapped(self) -> None:
        with (
            patch(
                "betabox_robotics.vision.detectors.face.cv2.CascadeClassifier",
                side_effect=cv2.error("cascade failed"),
            ),
            self.assertRaisesRegex(
                DetectorError,
                "failed to load face cascade",
            ),
        ):
            FaceDetector()


class FaceDetectorDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cascade = MagicMock()
        self.cascade.empty.return_value = False

        with patch(
            "betabox_robotics.vision.detectors.face.cv2.CascadeClassifier",
            return_value=self.cascade,
        ):
            self.detector = FaceDetector()

    def test_detect_requires_frame(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            self.detector.detect(
                object(),  # type: ignore[arg-type]
            )

    def test_detect_requires_numpy_image(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frame image must be a NumPy array",
        ):
            self.detector.detect(Frame.create(object()))

    def test_invalid_image_shape_returns_error_metadata(self) -> None:
        frame = Frame.create(
            np.zeros(
                (30, 30),
                dtype=np.uint8,
            ),
            timestamp=44.0,
        )

        metadata = self.detector.detect(frame)

        self.assertEqual(
            metadata.timestamp,
            44.0,
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
            "expected 3-channel image",
        )

    def test_detect_returns_face_metadata(self) -> None:
        self.cascade.detectMultiScale.return_value = np.array(
            [
                (
                    10,
                    20,
                    30,
                    40,
                ),
            ]
        )

        frame = Frame.create(
            np.zeros(
                (100, 100, 3),
                dtype=np.uint8,
            ),
            timestamp=123.5,
        )

        metadata = self.detector.detect(frame)

        self.assertEqual(
            metadata.timestamp,
            123.5,
        )
        self.assertEqual(
            metadata.data["count"],
            1,
        )

        detection = metadata.detections[0]

        self.assertEqual(
            detection.label,
            "face",
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
                "width": 30,
                "height": 40,
            },
        )

        self.cascade.detectMultiScale.assert_called_once()

    def test_detect_returns_empty_metadata_when_no_faces(self) -> None:
        self.cascade.detectMultiScale.return_value = ()

        metadata = self.detector.detect(
            Frame.create(
                np.zeros(
                    (50, 50, 3),
                    dtype=np.uint8,
                )
            )
        )

        self.assertEqual(
            metadata.detections,
            (),
        )
        self.assertEqual(
            metadata.data["count"],
            0,
        )

    def test_opencv_conversion_failure_is_wrapped(self) -> None:
        frame = Frame.create(
            np.zeros(
                (20, 20, 3),
                dtype=np.uint8,
            )
        )

        with (
            patch(
                "betabox_robotics.vision.detectors.face.cv2.cvtColor",
                side_effect=cv2.error("conversion failed"),
            ),
            self.assertRaisesRegex(
                DetectorError,
                "face detection failed",
            ),
        ):
            self.detector.detect(frame)

    def test_cascade_detection_failure_is_wrapped(self) -> None:
        self.cascade.detectMultiScale.side_effect = cv2.error("detection failed")

        frame = Frame.create(
            np.zeros(
                (20, 20, 3),
                dtype=np.uint8,
            )
        )

        with self.assertRaisesRegex(
            DetectorError,
            "face detection failed",
        ):
            self.detector.detect(frame)


if __name__ == "__main__":
    unittest.main()
