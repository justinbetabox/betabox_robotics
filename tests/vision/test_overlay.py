import unittest

import numpy as np
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata
from betabox_robotics.vision.overlay import (
    DEFAULT_COLORS,
    OverlayRenderer,
    OverlayStyle,
)


class OverlayRendererTests(unittest.TestCase):
    def test_default_style(self):
        renderer = OverlayRenderer()

        self.assertIsInstance(renderer.style, OverlayStyle)

    def test_custom_style(self):
        style = OverlayStyle(
            box_thickness=4,
            label_scale=1.0,
            label_thickness=2,
        )

        renderer = OverlayRenderer(style)

        self.assertIs(renderer.style, style)

    def test_draw_metadata_returns_new_frame(self):
        renderer = OverlayRenderer()

        image = np.zeros((100, 100, 3), dtype=np.uint8)
        frame = Frame.create(image)

        metadata = Metadata(
            source="test",
            timestamp=frame.timestamp,
        )

        result = renderer.draw_metadata(frame, metadata)

        self.assertIsNot(result, frame)
        self.assertIsNot(result.image, frame.image)
        self.assertEqual(result.timestamp, frame.timestamp)

    def test_draw_metadata_does_not_modify_original_image(self):
        renderer = OverlayRenderer()

        image = np.zeros((100, 100, 3), dtype=np.uint8)
        original = image.copy()

        frame = Frame.create(image)

        metadata = Metadata(
            source="test",
            timestamp=frame.timestamp,
            detections=(
                Detection(
                    label="person",
                    confidence=0.95,
                    box=(10, 10, 20, 20),
                ),
            ),
        )

        renderer.draw_metadata(frame, metadata)

        np.testing.assert_array_equal(frame.image, original)

    def test_detection_without_box_is_ignored(self):
        renderer = OverlayRenderer()

        image = np.zeros((100, 100, 3), dtype=np.uint8)
        frame = Frame.create(image)

        metadata = Metadata(
            source="test",
            timestamp=frame.timestamp,
            detections=(
                Detection(
                    label="person",
                    confidence=0.9,
                    box=None,
                ),
            ),
        )

        result = renderer.draw_metadata(frame, metadata)

        np.testing.assert_array_equal(result.image, frame.image)

    def test_detection_draws_overlay(self):
        renderer = OverlayRenderer()

        image = np.zeros((100, 100, 3), dtype=np.uint8)
        frame = Frame.create(image)

        metadata = Metadata(
            source="test",
            timestamp=frame.timestamp,
            detections=(
                Detection(
                    label="person",
                    confidence=0.95,
                    box=(10, 10, 20, 20),
                ),
            ),
        )

        result = renderer.draw_metadata(frame, metadata)

        self.assertFalse(np.array_equal(result.image, frame.image))

    def test_unknown_label_uses_default_color(self):
        renderer = OverlayRenderer()

        self.assertNotIn("banana", DEFAULT_COLORS)

    def test_known_colors_exist(self):
        self.assertIn("person", DEFAULT_COLORS)
        self.assertIn("face", DEFAULT_COLORS)
        self.assertIn("red", DEFAULT_COLORS)
        self.assertIn("green", DEFAULT_COLORS)
        self.assertIn("blue", DEFAULT_COLORS)
        self.assertIn("yellow", DEFAULT_COLORS)

    def test_invalid_style_values_raise(self):
        with self.assertRaises(ValueError):
            OverlayStyle(box_thickness=0)

        with self.assertRaises(ValueError):
            OverlayStyle(label_scale=0)

        with self.assertRaises(ValueError):
            OverlayStyle(label_thickness=0)
