import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.snapshot import (
    SnapshotError,
    SnapshotService,
    _normalize_image_format,
    _validate_directory,
    _validate_filename,
)


class FakeFrameProvider:
    def __init__(
        self,
        frame: Frame,
    ) -> None:
        self.frame = frame
        self.call_count = 0

    def latest_frame(self) -> Frame:
        self.call_count += 1
        return self.frame


def create_test_frame(
    *,
    timestamp: float = 123.5,
) -> Frame:
    return Frame.create(
        np.zeros(
            (20, 20, 3),
            dtype=np.uint8,
        ),
        timestamp=timestamp,
    )


class SnapshotValidationTests(unittest.TestCase):
    def test_normalize_image_format(self) -> None:
        cases = (
            (
                "jpg",
                "jpg",
            ),
            (
                " JPEG ",
                "jpg",
            ),
            (
                "PNG",
                "png",
            ),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    _normalize_image_format(value),
                    expected,
                )

    def test_normalize_image_format_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "image format must be a string",
        ):
            _normalize_image_format(123)

    def test_normalize_image_format_rejects_empty_format(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "image format cannot be empty",
        ):
            _normalize_image_format(" ")

    def test_normalize_image_format_rejects_unsupported_format(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unsupported snapshot format: gif",
        ):
            _normalize_image_format("gif")

    def test_validate_directory(self) -> None:
        self.assertEqual(
            _validate_directory(
                "pictures",
                name="directory",
            ),
            Path("pictures"),
        )

    def test_validate_directory_accepts_path(self) -> None:
        directory = Path("pictures")

        self.assertEqual(
            _validate_directory(
                directory,
                name="directory",
            ),
            directory,
        )

    def test_validate_directory_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            True,
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "directory must be a string or Path",
                ),
            ):
                _validate_directory(
                    value,
                    name="directory",
                )

    def test_validate_filename(self) -> None:
        self.assertEqual(
            _validate_filename("  picture.jpg  "),
            "picture.jpg",
        )

    def test_validate_filename_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "filename must be a string",
        ):
            _validate_filename(123)

    def test_validate_filename_rejects_empty_filename(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "filename cannot be empty",
        ):
            _validate_filename(" ")

    def test_validate_filename_rejects_directory_components(
        self,
    ) -> None:
        for value in (
            "folder/picture.jpg",
            "../picture.jpg",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "filename must not contain a directory",
                ),
            ):
                _validate_filename(value)


class SnapshotServiceConfigurationTests(unittest.TestCase):
    def test_default_configuration(self) -> None:
        provider = FakeFrameProvider(create_test_frame())

        service = SnapshotService(provider)

        self.assertIs(
            service.frame_source,
            provider,
        )
        self.assertEqual(
            service.directory,
            Path.home() / "media" / "pictures",
        )
        self.assertEqual(
            service.default_format,
            "jpg",
        )

    def test_custom_configuration(self) -> None:
        provider = FakeFrameProvider(create_test_frame())

        service = SnapshotService(
            provider,
            directory="custom-pictures",
            default_format="png",
        )

        self.assertEqual(
            service.directory,
            Path("custom-pictures"),
        )
        self.assertEqual(
            service.default_format,
            "png",
        )

    def test_normalizes_default_format(self) -> None:
        provider = FakeFrameProvider(create_test_frame())

        service = SnapshotService(
            provider,
            default_format="jpeg",
        )

        self.assertEqual(
            service.default_format,
            "jpg",
        )

    def test_requires_frame_provider(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            r"frame_source must provide latest_frame\(\)",
        ):
            SnapshotService(
                object(),  # type: ignore[arg-type]
            )

    def test_rejects_non_callable_latest_frame(self) -> None:
        provider = MagicMock()
        provider.latest_frame = None

        with self.assertRaisesRegex(
            TypeError,
            r"frame_source must provide latest_frame\(\)",
        ):
            SnapshotService(provider)

    def test_rejects_invalid_directory(self) -> None:
        provider = FakeFrameProvider(create_test_frame())

        with self.assertRaisesRegex(
            TypeError,
            "directory must be a string or Path",
        ):
            SnapshotService(
                provider,
                directory=123,  # type: ignore[arg-type]
            )


class SnapshotImagePreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SnapshotService(FakeFrameProvider(create_test_frame()))

    def test_prepare_rgb_image_converts_to_bgr(self) -> None:
        image = np.array(
            [
                [
                    (
                        255,
                        0,
                        10,
                    ),
                ],
            ],
            dtype=np.uint8,
        )

        prepared = self.service._prepare_image(Frame.create(image))

        np.testing.assert_array_equal(
            prepared,
            np.array(
                [
                    [
                        (
                            10,
                            0,
                            255,
                        ),
                    ],
                ],
                dtype=np.uint8,
            ),
        )

    def test_prepare_rgba_image_converts_to_bgra(self) -> None:
        image = np.array(
            [
                [
                    (
                        255,
                        0,
                        10,
                        200,
                    ),
                ],
            ],
            dtype=np.uint8,
        )

        prepared = self.service._prepare_image(Frame.create(image))

        np.testing.assert_array_equal(
            prepared,
            np.array(
                [
                    [
                        (
                            10,
                            0,
                            255,
                            200,
                        ),
                    ],
                ],
                dtype=np.uint8,
            ),
        )

    def test_prepare_grayscale_image_unchanged(self) -> None:
        image = np.zeros(
            (10, 10),
            dtype=np.uint8,
        )

        prepared = self.service._prepare_image(Frame.create(image))

        self.assertIs(
            prepared,
            image,
        )

    def test_prepare_single_channel_image_unchanged(
        self,
    ) -> None:
        image = np.zeros(
            (10, 10, 1),
            dtype=np.uint8,
        )

        prepared = self.service._prepare_image(Frame.create(image))

        self.assertIs(
            prepared,
            image,
        )

    def test_prepare_image_requires_numpy_array(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frame image must be a NumPy array",
        ):
            self.service._prepare_image(Frame.create(object()))

    def test_prepare_image_rejects_invalid_dimensions(
        self,
    ) -> None:
        image = np.zeros(
            (2, 2, 2, 2),
            dtype=np.uint8,
        )

        with self.assertRaisesRegex(
            SnapshotError,
            "snapshot image must be two- or three-dimensional",
        ):
            self.service._prepare_image(Frame.create(image))

    def test_prepare_image_rejects_unsupported_channels(
        self,
    ) -> None:
        image = np.zeros(
            (10, 10, 2),
            dtype=np.uint8,
        )

        with self.assertRaisesRegex(
            SnapshotError,
            "snapshot image has an unsupported channel count",
        ):
            self.service._prepare_image(Frame.create(image))

    def test_prepare_image_wraps_opencv_failure(
        self,
    ) -> None:
        image = np.zeros(
            (10, 10, 3),
            dtype=np.uint8,
        )

        with (
            patch(
                "betabox_robotics.vision.snapshot.cv2.cvtColor",
                side_effect=cv2.error("conversion failed"),
            ),
            self.assertRaisesRegex(
                SnapshotError,
                "failed to prepare snapshot image",
            ),
        ):
            self.service._prepare_image(Frame.create(image))


class SnapshotDataTests(unittest.TestCase):
    def test_capture_data_uses_latest_frame(self) -> None:
        frame = create_test_frame(
            timestamp=123.5,
        )
        provider = FakeFrameProvider(frame)
        service = SnapshotService(provider)

        result = service.capture_data(
            image_format="png",
        )

        self.assertEqual(
            provider.call_count,
            1,
        )
        self.assertEqual(
            result.timestamp,
            123.5,
        )
        self.assertEqual(
            result.format,
            "png",
        )
        self.assertIsInstance(
            result.data,
            bytes,
        )
        self.assertGreater(
            len(result.data),
            0,
        )

    def test_capture_frame_data_uses_default_format(
        self,
    ) -> None:
        service = SnapshotService(
            FakeFrameProvider(create_test_frame()),
            default_format="png",
        )

        result = service.capture_frame_data(create_test_frame())

        self.assertEqual(
            result.format,
            "png",
        )

    def test_capture_frame_data_normalizes_jpeg(
        self,
    ) -> None:
        service = SnapshotService(FakeFrameProvider(create_test_frame()))

        result = service.capture_frame_data(
            create_test_frame(
                timestamp=75.0,
            ),
            image_format="jpeg",
        )

        self.assertEqual(
            result.timestamp,
            75.0,
        )
        self.assertEqual(
            result.format,
            "jpg",
        )
        self.assertTrue(result.data.startswith(b"\xff\xd8"))

    def test_capture_frame_data_requires_frame(
        self,
    ) -> None:
        service = SnapshotService(FakeFrameProvider(create_test_frame()))

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            service.capture_frame_data(
                object(),  # type: ignore[arg-type]
            )

    def test_encoding_failure_is_wrapped(self) -> None:
        service = SnapshotService(FakeFrameProvider(create_test_frame()))

        with (
            patch(
                "betabox_robotics.vision.snapshot.cv2.imencode",
                side_effect=cv2.error("encoding failed"),
            ),
            self.assertRaisesRegex(
                SnapshotError,
                "failed to encode snapshot as jpg",
            ),
        ):
            service.capture_frame_data(create_test_frame())

    def test_unsuccessful_encoding_raises(self) -> None:
        service = SnapshotService(FakeFrameProvider(create_test_frame()))

        encoded = np.array(
            [],
            dtype=np.uint8,
        )

        with (
            patch(
                "betabox_robotics.vision.snapshot.cv2.imencode",
                return_value=(
                    False,
                    encoded,
                ),
            ),
            self.assertRaisesRegex(
                SnapshotError,
                "failed to encode snapshot as jpg",
            ),
        ):
            service.capture_frame_data(create_test_frame())


class SnapshotFileTests(unittest.TestCase):
    def test_capture_uses_latest_frame(self) -> None:
        frame = create_test_frame(
            timestamp=123.5,
        )
        provider = FakeFrameProvider(frame)

        with tempfile.TemporaryDirectory() as temp_dir:
            service = SnapshotService(
                provider,
                directory=temp_dir,
            )

            result = service.capture(
                filename="picture",
                image_format="png",
            )

            self.assertEqual(
                provider.call_count,
                1,
            )
            self.assertEqual(
                result.timestamp,
                123.5,
            )
            self.assertEqual(
                result.format,
                "png",
            )
            self.assertEqual(
                result.path,
                Path(temp_dir) / "picture.png",
            )
            self.assertTrue(result.path.is_file())

    def test_capture_frame_uses_default_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = SnapshotService(
                FakeFrameProvider(create_test_frame()),
                directory=temp_dir,
            )

            result = service.capture_frame(
                create_test_frame(),
                filename="picture",
            )

            self.assertEqual(
                result.path,
                Path(temp_dir) / "picture.jpg",
            )
            self.assertEqual(
                result.format,
                "jpg",
            )
            self.assertTrue(result.path.is_file())

    def test_capture_frame_uses_override_directory(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as default_dir,
            tempfile.TemporaryDirectory() as override_dir,
        ):
            service = SnapshotService(
                FakeFrameProvider(create_test_frame()),
                directory=default_dir,
            )

            result = service.capture_frame(
                create_test_frame(),
                filename="picture",
                directory=override_dir,
                image_format="png",
            )

            self.assertEqual(
                result.path,
                Path(override_dir) / "picture.png",
            )
            self.assertTrue(result.path.is_file())

    def test_capture_frame_replaces_conflicting_extension(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = SnapshotService(
                FakeFrameProvider(create_test_frame()),
                directory=temp_dir,
            )

            result = service.capture_frame(
                create_test_frame(),
                filename="picture.jpg",
                image_format="png",
            )

            self.assertEqual(
                result.path.name,
                "picture.png",
            )
            self.assertEqual(
                result.format,
                "png",
            )

    def test_capture_frame_adds_extension(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = SnapshotService(
                FakeFrameProvider(create_test_frame()),
                directory=temp_dir,
            )

            result = service.capture_frame(
                create_test_frame(),
                filename="picture",
                image_format="jpg",
            )

            self.assertEqual(
                result.path.name,
                "picture.jpg",
            )

    def test_capture_frame_generates_filename(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = SnapshotService(
                FakeFrameProvider(create_test_frame()),
                directory=temp_dir,
            )

            with patch(
                "betabox_robotics.vision.snapshot.strftime",
                return_value="20260804_121500",
            ):
                result = service.capture_frame(
                    create_test_frame(),
                    image_format="png",
                )

            self.assertEqual(
                result.path.name,
                "snapshot_20260804_121500.png",
            )

    def test_capture_frame_requires_frame(self) -> None:
        service = SnapshotService(FakeFrameProvider(create_test_frame()))

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            service.capture_frame(
                object(),  # type: ignore[arg-type]
            )

    def test_directory_creation_failure_is_wrapped(
        self,
    ) -> None:
        service = SnapshotService(FakeFrameProvider(create_test_frame()))
        directory = MagicMock(spec=Path)
        directory.mkdir.side_effect = OSError("permission denied")

        with (
            patch(
                "betabox_robotics.vision.snapshot._validate_directory",
                return_value=directory,
            ),
            self.assertRaisesRegex(
                SnapshotError,
                "failed to create snapshot directory",
            ),
        ):
            service.capture_frame(
                create_test_frame(),
                directory="pictures",
            )

    def test_write_failure_is_wrapped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = SnapshotService(
                FakeFrameProvider(create_test_frame()),
                directory=temp_dir,
            )

            with (
                patch(
                    "betabox_robotics.vision.snapshot.cv2.imwrite",
                    side_effect=cv2.error("write failed"),
                ),
                self.assertRaisesRegex(
                    SnapshotError,
                    "failed to write snapshot",
                ),
            ):
                service.capture_frame(
                    create_test_frame(),
                    filename="picture.jpg",
                )

    def test_unsuccessful_write_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = SnapshotService(
                FakeFrameProvider(create_test_frame()),
                directory=temp_dir,
            )

            with (
                patch(
                    "betabox_robotics.vision.snapshot.cv2.imwrite",
                    return_value=False,
                ),
                self.assertRaisesRegex(
                    SnapshotError,
                    "failed to write snapshot",
                ),
            ):
                service.capture_frame(
                    create_test_frame(),
                    filename="picture.jpg",
                )


if __name__ == "__main__":
    unittest.main()
