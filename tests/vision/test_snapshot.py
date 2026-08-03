import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.interfaces import FrameProvider
from betabox_robotics.vision.snapshot import (
    Snapshot,
    SnapshotData,
    SnapshotError,
    SnapshotService,
)


class SnapshotServiceTests(unittest.TestCase):
    def setUp(self):
        self.provider = MagicMock(spec=FrameProvider)
        self.image = np.zeros((32, 32, 3), dtype=np.uint8)
        self.frame = Frame.create(self.image)

    def test_default_configuration(self):
        service = SnapshotService(self.provider)

        self.assertIs(service.frame_source, self.provider)
        self.assertEqual(
            service.directory,
            Path.home() / "media" / "pictures",
        )
        self.assertEqual(service.default_format, "jpg")

    def test_custom_configuration(self):
        service = SnapshotService(
            self.provider,
            directory="/tmp/snapshots",
            default_format="png",
        )

        self.assertEqual(service.directory, Path("/tmp/snapshots"))
        self.assertEqual(service.default_format, "png")

    def test_jpeg_default_format_is_normalized(self):
        service = SnapshotService(
            self.provider,
            default_format="jpeg",
        )

        self.assertEqual(service.default_format, "jpg")

    def test_invalid_default_format_raises(self):
        with self.assertRaises(ValueError):
            SnapshotService(
                self.provider,
                default_format="gif",  # type: ignore[arg-type]
            )

    def test_capture_frame_data_encodes_jpg(self):
        service = SnapshotService(self.provider)

        result = service.capture_frame_data(
            self.frame,
            image_format="jpg",
        )

        self.assertIsInstance(result, SnapshotData)
        self.assertIsInstance(result.data, bytes)
        self.assertGreater(len(result.data), 0)
        self.assertEqual(result.timestamp, self.frame.timestamp)
        self.assertEqual(result.format, "jpg")

    def test_capture_frame_data_encodes_png(self):
        service = SnapshotService(self.provider)

        result = service.capture_frame_data(
            self.frame,
            image_format="png",
        )

        self.assertIsInstance(result.data, bytes)
        self.assertGreater(len(result.data), 0)
        self.assertEqual(result.format, "png")

    def test_capture_frame_data_normalizes_jpeg_alias(self):
        service = SnapshotService(self.provider)

        result = service.capture_frame_data(
            self.frame,
            image_format="jpeg",
        )

        self.assertEqual(result.format, "jpg")

    def test_capture_frame_data_rejects_unsupported_format(self):
        service = SnapshotService(self.provider)

        with self.assertRaises(SnapshotError):
            service.capture_frame_data(
                self.frame,
                image_format="gif",  # type: ignore[arg-type]
            )

    @patch("betabox_robotics.vision.snapshot.cv2.imencode")
    def test_capture_frame_data_handles_encode_failure(
        self,
        imencode,
    ):
        imencode.return_value = (
            False,
            np.array([], dtype=np.uint8),
        )

        service = SnapshotService(self.provider)

        with self.assertRaisesRegex(
            SnapshotError,
            "failed to encode snapshot as jpg",
        ):
            service.capture_frame_data(self.frame)

    @patch("betabox_robotics.vision.snapshot.cv2.imencode")
    def test_capture_frame_data_wraps_opencv_error(
        self,
        imencode,
    ):
        imencode.side_effect = cv2.error("boom")

        service = SnapshotService(self.provider)

        with self.assertRaisesRegex(
            SnapshotError,
            "failed to encode snapshot as jpg",
        ):
            service.capture_frame_data(self.frame)

    def test_capture_frame_creates_directory_and_writes_file(self):
        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "pictures"
            service = SnapshotService(
                self.provider,
                directory=output_directory,
            )

            result = service.capture_frame(
                self.frame,
                filename="photo.jpg",
            )

            self.assertIsInstance(result, Snapshot)
            self.assertEqual(
                result.path,
                output_directory / "photo.jpg",
            )
            self.assertTrue(result.path.is_file())
            self.assertEqual(result.timestamp, self.frame.timestamp)
            self.assertEqual(result.format, "jpg")

    def test_capture_frame_adds_missing_extension(self):
        with TemporaryDirectory() as temporary_directory:
            service = SnapshotService(
                self.provider,
                directory=temporary_directory,
            )

            result = service.capture_frame(
                self.frame,
                filename="photo",
                image_format="png",
            )

            self.assertEqual(result.path.name, "photo.png")
            self.assertEqual(result.format, "png")
            self.assertTrue(result.path.is_file())

    def test_capture_frame_uses_custom_directory(self):
        with TemporaryDirectory() as temporary_directory:
            default_directory = Path(temporary_directory) / "default"
            custom_directory = Path(temporary_directory) / "custom"

            service = SnapshotService(
                self.provider,
                directory=default_directory,
            )

            result = service.capture_frame(
                self.frame,
                filename="photo.jpg",
                directory=custom_directory,
            )

            self.assertEqual(
                result.path,
                custom_directory / "photo.jpg",
            )
            self.assertTrue(result.path.is_file())
            self.assertFalse(default_directory.exists())

    @patch(
        "betabox_robotics.vision.snapshot.strftime",
        return_value="20260730_153000",
    )
    def test_capture_frame_generates_filename(self, strftime_mock):
        with TemporaryDirectory() as temporary_directory:
            service = SnapshotService(
                self.provider,
                directory=temporary_directory,
            )

            result = service.capture_frame(self.frame)

            self.assertEqual(
                result.path.name,
                "snapshot_20260730_153000.jpg",
            )
            strftime_mock.assert_called_once_with("%Y%m%d_%H%M%S")

    @patch(
        "betabox_robotics.vision.snapshot.cv2.imwrite",
        return_value=False,
    )
    def test_capture_frame_handles_write_failure(self, imwrite):
        with TemporaryDirectory() as temporary_directory:
            service = SnapshotService(
                self.provider,
                directory=temporary_directory,
            )

            with self.assertRaisesRegex(
                SnapshotError,
                "failed to write snapshot",
            ):
                service.capture_frame(
                    self.frame,
                    filename="photo.jpg",
                )

            imwrite.assert_called_once()

    @patch("betabox_robotics.vision.snapshot.cv2.imwrite")
    def test_capture_frame_wraps_opencv_write_error(self, imwrite):
        imwrite.side_effect = cv2.error("boom")

        with TemporaryDirectory() as temporary_directory:
            service = SnapshotService(
                self.provider,
                directory=temporary_directory,
            )

            with self.assertRaisesRegex(
                SnapshotError,
                "failed to write snapshot",
            ):
                service.capture_frame(
                    self.frame,
                    filename="photo.jpg",
                )

    @patch("betabox_robotics.vision.snapshot.Path.mkdir")
    def test_capture_frame_wraps_directory_creation_error(self, mkdir):
        mkdir.side_effect = OSError("permission denied")

        service = SnapshotService(
            self.provider,
            directory="/unavailable/pictures",
        )

        with self.assertRaisesRegex(
            SnapshotError,
            "failed to create snapshot directory",
        ):
            service.capture_frame(
                self.frame,
                filename="photo.jpg",
            )

    def test_capture_retrieves_latest_frame(self):
        self.provider.latest_frame.return_value = self.frame

        service = SnapshotService(self.provider)

        expected = Snapshot(
            path=Path("/tmp/photo.jpg"),
            timestamp=self.frame.timestamp,
            format="jpg",
        )

        with patch.object(
            service,
            "capture_frame",
            return_value=expected,
        ) as capture_frame:
            result = service.capture(
                filename="photo.jpg",
                directory="/tmp",
                image_format="jpg",
            )

        self.provider.latest_frame.assert_called_once_with()
        capture_frame.assert_called_once_with(
            self.frame,
            filename="photo.jpg",
            directory="/tmp",
            image_format="jpg",
        )
        self.assertIs(result, expected)

    def test_capture_data_retrieves_latest_frame(self):
        self.provider.latest_frame.return_value = self.frame

        service = SnapshotService(self.provider)

        expected = SnapshotData(
            data=b"image",
            timestamp=self.frame.timestamp,
            format="png",
        )

        with patch.object(
            service,
            "capture_frame_data",
            return_value=expected,
        ) as capture_frame_data:
            result = service.capture_data(image_format="png")

        self.provider.latest_frame.assert_called_once_with()
        capture_frame_data.assert_called_once_with(
            self.frame,
            image_format="png",
        )
        self.assertIs(result, expected)


if __name__ == "__main__":
    unittest.main()
