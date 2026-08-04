import unittest
from unittest.mock import patch

import cv2
import numpy as np

from betabox_robotics.vision.detector import DetectorError
from betabox_robotics.vision.detectors.color import (
    ColorDetector,
    _validate_colors,
    _validate_custom_ranges,
    _validate_hsv_range,
    _validate_hsv_value,
    _validate_min_area,
)
from betabox_robotics.vision.frame import Frame


class ColorValidationTests(unittest.TestCase):
    def test_validate_hsv_value(self) -> None:
        self.assertEqual(
            _validate_hsv_value(
                (10, 100, 200),
                name="test",
            ),
            (10, 100, 200),
        )

    def test_validate_hsv_value_rejects_invalid_shape(self) -> None:
        for value in (
            (10, 100),
            [10, 100, 200],
            "10,100,200",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                _validate_hsv_value(
                    value,
                    name="test",
                )

    def test_validate_hsv_value_rejects_invalid_components(self) -> None:
        for value in (
            (True, 100, 200),
            (10.0, 100, 200),
            (10, "100", 200),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "test must contain three integers",
                ),
            ):
                _validate_hsv_value(
                    value,
                    name="test",
                )

    def test_validate_hsv_value_rejects_out_of_range_values(self) -> None:
        cases = (
            (
                (-1, 100, 200),
                "hue must be between 0 and 180",
            ),
            (
                (181, 100, 200),
                "hue must be between 0 and 180",
            ),
            (
                (10, -1, 200),
                "saturation must be between 0 and 255",
            ),
            (
                (10, 256, 200),
                "saturation must be between 0 and 255",
            ),
            (
                (10, 100, -1),
                "brightness must be between 0 and 255",
            ),
            (
                (10, 100, 256),
                "brightness must be between 0 and 255",
            ),
        )

        for value, message in cases:
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    message,
                ),
            ):
                _validate_hsv_value(
                    value,
                    name="test",
                )

    def test_validate_hsv_range(self) -> None:
        hsv_range = (
            (10, 100, 100),
            (20, 255, 255),
        )

        self.assertEqual(
            _validate_hsv_range(
                hsv_range,
                name="orange",
            ),
            hsv_range,
        )

    def test_validate_hsv_range_rejects_reversed_bounds(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "lower values cannot exceed upper values",
        ):
            _validate_hsv_range(
                (
                    (20, 100, 100),
                    (10, 255, 255),
                ),
                name="test",
            )

    def test_validate_custom_ranges_accepts_single_range(self) -> None:
        ranges = _validate_custom_ranges(
            {
                " Team Marker ": (
                    (10, 100, 100),
                    (20, 255, 255),
                ),
            }
        )

        self.assertEqual(
            ranges,
            {
                "team marker": (
                    (
                        (10, 100, 100),
                        (20, 255, 255),
                    ),
                ),
            },
        )

    def test_validate_custom_ranges_accepts_multiple_ranges(self) -> None:
        ranges = _validate_custom_ranges(
            {
                "custom_red": (
                    (
                        (0, 100, 100),
                        (10, 255, 255),
                    ),
                    (
                        (170, 100, 100),
                        (180, 255, 255),
                    ),
                ),
            }
        )

        self.assertEqual(
            len(ranges["custom_red"]),
            2,
        )

    def test_validate_custom_ranges_rejects_invalid_mapping(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "custom_ranges must be a mapping",
        ):
            _validate_custom_ranges(
                [  # type: ignore[arg-type]
                    (
                        "red",
                        (
                            (0, 100, 100),
                            (10, 255, 255),
                        ),
                    ),
                ]
            )

    def test_validate_colors_normalizes_and_deduplicates(self) -> None:
        supported = {
            "red": (),
            "blue": (),
        }

        self.assertEqual(
            _validate_colors(
                [
                    " Red ",
                    "BLUE",
                    "red",
                ],
                supported=supported,
            ),
            [
                "red",
                "blue",
            ],
        )

    def test_validate_colors_rejects_unsupported_color(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"unsupported color\(s\): purple",
        ):
            _validate_colors(
                "purple",
                supported={
                    "red": (),
                },
            )

    def test_validate_min_area(self) -> None:
        self.assertEqual(
            _validate_min_area(500),
            500.0,
        )

    def test_validate_min_area_rejects_invalid_values(self) -> None:
        for value in (
            True,
            "500",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "min_area must be a number",
                ),
            ):
                _validate_min_area(value)

        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "min_area must be finite",
                ),
            ):
                _validate_min_area(value)

        with self.assertRaisesRegex(
            ValueError,
            "min_area cannot be negative",
        ):
            _validate_min_area(-1)


class ColorDetectorConfigurationTests(unittest.TestCase):
    def test_default_configuration(self) -> None:
        detector = ColorDetector()

        self.assertEqual(
            detector.name,
            "color",
        )
        self.assertEqual(
            detector.colors,
            ["red"],
        )
        self.assertEqual(
            detector.min_area,
            500.0,
        )
        self.assertFalse(detector.enabled)

    def test_available_colors_include_expanded_defaults(self) -> None:
        detector = ColorDetector()

        available = detector.available_colors()

        for color in (
            "red",
            "orange",
            "yellow",
            "lime",
            "green",
            "teal",
            "cyan",
            "blue",
            "purple",
            "magenta",
            "pink",
            "white",
            "gray",
            "black",
        ):
            with self.subTest(color=color):
                self.assertIn(
                    color,
                    available,
                )

    def test_custom_color_is_available(self) -> None:
        detector = ColorDetector(
            colors="team_marker",
            custom_ranges={
                "team_marker": (
                    (10, 100, 100),
                    (20, 255, 255),
                ),
            },
        )

        self.assertEqual(
            detector.colors,
            ["team_marker"],
        )
        self.assertIn(
            "team_marker",
            detector.available_colors(),
        )

    def test_configure_updates_colors_and_min_area(self) -> None:
        detector = ColorDetector()

        detector.configure(
            [
                "blue",
                "green",
            ],
            min_area=25,
        )

        self.assertEqual(
            detector.colors,
            [
                "blue",
                "green",
            ],
        )
        self.assertEqual(
            detector.min_area,
            25.0,
        )

    def test_enable_configures_and_enables_detector(self) -> None:
        detector = ColorDetector()

        detector.enable(
            "orange",
            min_area=10,
        )

        self.assertTrue(detector.enabled)
        self.assertEqual(
            detector.colors,
            ["orange"],
        )
        self.assertEqual(
            detector.min_area,
            10.0,
        )


class ColorDetectorDetectionTests(unittest.TestCase):
    def test_detect_requires_frame(self) -> None:
        detector = ColorDetector()

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            detector.detect(
                object(),  # type: ignore[arg-type]
            )

    def test_detect_requires_numpy_image(self) -> None:
        detector = ColorDetector()

        with self.assertRaisesRegex(
            TypeError,
            "frame image must be a NumPy array",
        ):
            detector.detect(Frame.create(object()))

    def test_invalid_image_shape_returns_error_metadata(self) -> None:
        detector = ColorDetector(
            colors=[
                "red",
                "blue",
            ],
        )

        frame = Frame.create(
            np.zeros(
                (30, 30),
                dtype=np.uint8,
            ),
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
            metadata.data["counts"],
            {
                "red": 0,
                "blue": 0,
            },
        )
        self.assertEqual(
            metadata.data["error"],
            "expected 3-channel image",
        )

    def test_detects_red_region(self) -> None:
        detector = ColorDetector(
            colors="red",
            min_area=10,
        )

        image = np.zeros(
            (60, 60, 3),
            dtype=np.uint8,
        )
        image[10:40, 15:45] = (
            255,
            0,
            0,
        )

        frame = Frame.create(
            image,
            timestamp=50.0,
        )

        metadata = detector.detect(frame)

        self.assertEqual(
            metadata.timestamp,
            50.0,
        )
        self.assertEqual(
            metadata.data["count"],
            1,
        )
        self.assertEqual(
            metadata.data["counts"]["red"],
            1,
        )

        detection = metadata.detections[0]

        self.assertEqual(
            detection.label,
            "red",
        )
        self.assertIsNotNone(
            detection.box,
        )
        self.assertIsNotNone(
            detection.center,
        )
        self.assertGreater(
            detection.data["area"],
            10,
        )

    def test_min_area_filters_small_region(self) -> None:
        detector = ColorDetector(
            colors="red",
            min_area=500,
        )

        image = np.zeros(
            (40, 40, 3),
            dtype=np.uint8,
        )
        image[5:10, 5:10] = (
            255,
            0,
            0,
        )

        metadata = detector.detect(Frame.create(image))

        self.assertEqual(
            metadata.data["count"],
            0,
        )

    def test_custom_range_is_used_for_detection(self) -> None:
        detector = ColorDetector(
            colors="everything",
            custom_ranges={
                "everything": (
                    (0, 0, 0),
                    (180, 255, 255),
                ),
            },
            min_area=1,
        )

        image = np.zeros(
            (30, 30, 3),
            dtype=np.uint8,
        )

        metadata = detector.detect(Frame.create(image))

        self.assertEqual(
            metadata.data["count"],
            1,
        )
        self.assertEqual(
            metadata.detections[0].label,
            "everything",
        )

    def test_opencv_failure_is_wrapped(self) -> None:
        detector = ColorDetector()

        frame = Frame.create(
            np.zeros(
                (20, 20, 3),
                dtype=np.uint8,
            )
        )

        with (
            patch(
                "betabox_robotics.vision.detectors.color.cv2.cvtColor",
                side_effect=cv2.error("conversion failed"),
            ),
            self.assertRaisesRegex(
                DetectorError,
                "color detection failed",
            ),
        ):
            detector.detect(frame)


if __name__ == "__main__":
    unittest.main()
