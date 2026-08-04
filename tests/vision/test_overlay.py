import unittest

import numpy as np

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Detection, Metadata
from betabox_robotics.vision.overlay import (
    OverlayError,
    OverlayRenderer,
    OverlayStyle,
)


class OverlayStyleTests(unittest.TestCase):
    def test_default_style(self) -> None:
        style = OverlayStyle()

        self.assertEqual(style.box_thickness, 2)
        self.assertEqual(style.label_scale, 0.5)
        self.assertEqual(style.label_thickness, 1)

    def test_label_scale_is_normalized_to_float(self) -> None:
        style = OverlayStyle(
            label_scale=1,
        )

        self.assertEqual(style.label_scale, 1.0)
        self.assertIsInstance(
            style.label_scale,
            float,
        )

    def test_rejects_invalid_box_thickness(self) -> None:
        for value in (
            True,
            1.5,
            "2",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "box_thickness must be an integer",
                ),
            ):
                OverlayStyle(
                    box_thickness=value,  # type: ignore[arg-type]
                )

        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "box_thickness must be greater than zero",
                ),
            ):
                OverlayStyle(
                    box_thickness=value,
                )

    def test_rejects_invalid_label_scale(self) -> None:
        for value in (
            True,
            "0.5",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "label_scale must be a number",
                ),
            ):
                OverlayStyle(
                    label_scale=value,  # type: ignore[arg-type]
                )

        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "label_scale must be finite",
                ),
            ):
                OverlayStyle(
                    label_scale=value,
                )

        for value in (
            0,
            -0.5,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "label_scale must be greater than zero",
                ),
            ):
                OverlayStyle(
                    label_scale=value,
                )

    def test_rejects_invalid_label_thickness(self) -> None:
        for value in (
            True,
            1.5,
            "1",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "label_thickness must be an integer",
                ),
            ):
                OverlayStyle(
                    label_thickness=value,  # type: ignore[arg-type]
                )

        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "label_thickness must be greater than zero",
                ),
            ):
                OverlayStyle(
                    label_thickness=value,
                )


class OverlayRendererTests(unittest.TestCase):
    def test_default_style_created(self) -> None:
        renderer = OverlayRenderer()

        self.assertIsInstance(
            renderer.style,
            OverlayStyle,
        )
        self.assertEqual(
            renderer.style,
            OverlayStyle(),
        )

    def test_custom_style_used(self) -> None:
        style = OverlayStyle(
            box_thickness=4,
            label_scale=0.75,
            label_thickness=2,
        )

        renderer = OverlayRenderer(style)

        self.assertIs(
            renderer.style,
            style,
        )

    def test_rejects_invalid_style_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "style must be an OverlayStyle",
        ):
            OverlayRenderer(
                object(),  # type: ignore[arg-type]
            )

    def test_draw_metadata_returns_new_frame(self) -> None:
        image = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )
        original = image.copy()

        frame = Frame.create(
            image,
            timestamp=123.5,
        )
        metadata = Metadata.create(
            "face",
            timestamp=123.5,
            detections=[
                Detection(
                    label="face",
                    confidence=0.9,
                    box=(10, 10, 30, 30),
                ),
            ],
        )

        rendered = OverlayRenderer().draw_metadata(
            frame,
            metadata,
        )

        self.assertIsNot(
            rendered,
            frame,
        )
        self.assertIsNot(
            rendered.image,
            frame.image,
        )
        self.assertEqual(
            rendered.timestamp,
            frame.timestamp,
        )
        np.testing.assert_array_equal(
            frame.image,
            original,
        )
        self.assertFalse(
            np.array_equal(
                rendered.image,
                original,
            )
        )

    def test_detection_without_box_is_ignored(self) -> None:
        image = np.zeros(
            (100, 100, 3),
            dtype=np.uint8,
        )

        frame = Frame.create(image)
        metadata = Metadata.create(
            "face",
            detections=[
                Detection(
                    label="face",
                ),
            ],
        )

        rendered = OverlayRenderer().draw_metadata(
            frame,
            metadata,
        )

        np.testing.assert_array_equal(
            rendered.image,
            image,
        )
        self.assertIsNot(
            rendered.image,
            image,
        )

    def test_detection_box_is_clipped_to_image(self) -> None:
        image = np.zeros(
            (50, 50, 3),
            dtype=np.uint8,
        )

        frame = Frame.create(image)
        metadata = Metadata.create(
            "object",
            detections=[
                Detection(
                    label="object",
                    box=(-20, -20, 100, 100),
                ),
            ],
        )

        rendered = OverlayRenderer().draw_metadata(
            frame,
            metadata,
        )

        self.assertEqual(
            rendered.image.shape,
            image.shape,
        )
        self.assertFalse(
            np.array_equal(
                rendered.image,
                image,
            )
        )

    def test_invalid_detection_box_is_ignored(self) -> None:
        image = np.zeros(
            (50, 50, 3),
            dtype=np.uint8,
        )

        frame = Frame.create(image)
        metadata = Metadata.create(
            "object",
            detections=[
                Detection(
                    label="object",
                    box=(20, 20, -10, -10),
                ),
            ],
        )

        rendered = OverlayRenderer().draw_metadata(
            frame,
            metadata,
        )

        np.testing.assert_array_equal(
            rendered.image,
            image,
        )

    def test_draw_metadata_requires_frame(self) -> None:
        metadata = Metadata.create("test")

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            OverlayRenderer().draw_metadata(
                object(),  # type: ignore[arg-type]
                metadata,
            )

    def test_draw_metadata_requires_metadata(self) -> None:
        frame = Frame.create(
            np.zeros(
                (20, 20, 3),
                dtype=np.uint8,
            )
        )

        with self.assertRaisesRegex(
            TypeError,
            "metadata must be a Metadata instance",
        ):
            OverlayRenderer().draw_metadata(
                frame,
                object(),  # type: ignore[arg-type]
            )

    def test_draw_metadata_requires_numpy_image(self) -> None:
        frame = Frame.create(object())
        metadata = Metadata.create("test")

        with self.assertRaisesRegex(
            TypeError,
            "frame image must be a NumPy array",
        ):
            OverlayRenderer().draw_metadata(
                frame,
                metadata,
            )

    def test_draw_metadata_requires_three_channel_image(self) -> None:
        metadata = Metadata.create("test")

        for image in (
            np.zeros(
                (20, 20),
                dtype=np.uint8,
            ),
            np.zeros(
                (20, 20, 1),
                dtype=np.uint8,
            ),
            np.zeros(
                (20, 20, 4),
                dtype=np.uint8,
            ),
        ):
            with (
                self.subTest(shape=image.shape),
                self.assertRaisesRegex(
                    OverlayError,
                    "overlay rendering requires a three-channel image",
                ),
            ):
                OverlayRenderer().draw_metadata(
                    Frame.create(image),
                    metadata,
                )


if __name__ == "__main__":
    unittest.main()
