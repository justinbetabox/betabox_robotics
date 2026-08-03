import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer
from betabox_robotics.vision.recording import (
    Recording,
    RecordingData,
    RecordingError,
    RecordingService,
)


class RecordingModelTests(unittest.TestCase):
    def test_duration(self):
        recording = Recording(
            path=Path("/tmp/test.mp4"),
            start_timestamp=10.0,
            end_timestamp=13.5,
            frame_count=70,
            fps=20.0,
        )

        self.assertEqual(recording.duration, 3.5)

    def test_duration_never_negative(self):
        recording = Recording(
            path=Path("/tmp/test.mp4"),
            start_timestamp=20.0,
            end_timestamp=10.0,
            frame_count=0,
            fps=20.0,
        )

        self.assertEqual(recording.duration, 0.0)


class RecordingConfigurationTests(unittest.TestCase):
    def test_defaults(self):
        service = RecordingService()

        self.assertEqual(service.directory, Path("/tmp/betabox-video"))
        self.assertEqual(service.fps, 20.0)
        self.assertEqual(service.filename_prefix, "recording")
        self.assertFalse(service.overlay_enabled)
        self.assertIsNone(service.overlay_source)

    def test_custom_configuration(self):
        bus = MetadataBus()
        overlay = OverlayRenderer()

        service = RecordingService(
            directory="/tmp/video",
            fps=15,
            filename_prefix="lesson",
            metadata_bus=bus,
            overlay=overlay,
        )

        self.assertEqual(service.directory, Path("/tmp/video"))
        self.assertEqual(service.fps, 15.0)
        self.assertEqual(service.filename_prefix, "lesson")
        self.assertIs(service.metadata_bus, bus)
        self.assertIs(service.overlay, overlay)

    def test_invalid_fps(self):
        with self.assertRaises(RecordingError):
            RecordingService(fps=0)

        with self.assertRaises(RecordingError):
            RecordingService(fps=-5)


class RecordingOverlayTests(unittest.TestCase):
    def test_enable_overlay(self):
        service = RecordingService()

        service.enable_overlay("detector")

        self.assertTrue(service.overlay_enabled)
        self.assertEqual(service.overlay_source, "detector")

    def test_disable_overlay(self):
        service = RecordingService()

        service.enable_overlay("detector")
        service.disable_overlay()

        self.assertFalse(service.overlay_enabled)
        self.assertIsNone(service.overlay_source)

    def test_overlay_status(self):
        service = RecordingService()

        self.assertEqual(
            service.overlay_status(),
            {
                "enabled": False,
                "source": None,
            },
        )

        service.enable_overlay("vision")

        self.assertEqual(
            service.overlay_status(),
            {
                "enabled": True,
                "source": "vision",
            },
        )


class RecordingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.service = RecordingService(
            directory=self.tempdir.name,
        )

    def test_initial_state(self):
        self.assertFalse(self.service.is_recording())
        self.assertIsNone(self.service.last_error())

    @patch("betabox_robotics.vision.recording.shutil.which")
    @patch("betabox_robotics.vision.recording.threading.Thread")
    def test_start(
        self,
        thread,
        which,
    ):
        which.return_value = "/usr/bin/ffmpeg"

        thread.return_value = Mock()

        path = self.service.start()

        self.assertTrue(self.service.is_recording())
        self.assertEqual(path.suffix, ".mp4")
        thread.return_value.start.assert_called_once()

    @patch("betabox_robotics.vision.recording.shutil.which")
    def test_double_start(
        self,
        which,
    ):
        which.return_value = "/usr/bin/ffmpeg"

        worker = Mock()

        with patch(
            "betabox_robotics.vision.recording.threading.Thread",
            return_value=worker,
        ):
            self.service.start()

            with self.assertRaises(RecordingError):
                self.service.start()

    @patch("betabox_robotics.vision.recording.shutil.which")
    def test_missing_ffmpeg(
        self,
        which,
    ):
        which.return_value = None

        with self.assertRaisesRegex(
            RecordingError,
            "ffmpeg is not installed",
        ):
            self.service.start()

    def test_stop_without_start(self):
        with self.assertRaisesRegex(
            RecordingError,
            "recording is not running",
        ):
            self.service.stop()


class RecordingWriterTests(unittest.TestCase):
    def setUp(self):
        self.service = RecordingService()

        self.frame = Frame.create(
            np.zeros(
                (20, 30, 3),
                dtype=np.uint8,
            )
        )

    def test_invalid_channel_count(self):
        frame = Frame.create(
            np.zeros(
                (20, 30),
                dtype=np.uint8,
            )
        )

        with self.assertRaisesRegex(
            RecordingError,
            "3-channel",
        ):
            self.service._write_frame(frame)


class RecordingStopDataTests(unittest.TestCase):
    def test_stop_data(self):
        service = RecordingService()

        recording = Recording(
            path=Path("/tmp/test.mp4"),
            start_timestamp=1.0,
            end_timestamp=2.0,
            frame_count=10,
            fps=20,
        )

        with (
            patch.object(
                service,
                "stop",
                return_value=recording,
            ),
            patch.object(
                Path,
                "read_bytes",
                return_value=b"video",
            ),
            patch.object(
                Path,
                "unlink",
            ),
        ):
            result = service.stop_data()

        self.assertIsInstance(result, RecordingData)
        self.assertEqual(result.data, b"video")
        self.assertEqual(result.format, "mp4")
        self.assertEqual(result.frame_count, 10)

    def test_stop_data_removes_file_when_read_fails(self):
        service = RecordingService()

        recording = Recording(
            path=Path("/tmp/test.mp4"),
            start_timestamp=1.0,
            end_timestamp=2.0,
            frame_count=10,
            fps=20,
        )

        with (
            patch.object(service, "stop", return_value=recording),
            patch.object(Path, "read_bytes", side_effect=OSError("boom")),
            patch.object(Path, "unlink") as unlink,
            self.assertRaises(OSError),
        ):
            service.stop_data()

        unlink.assert_called_once()


class RecordingFailureTests(unittest.TestCase):
    @patch("betabox_robotics.vision.recording.shutil.which")
    def test_start_rejects_filename_with_directory(self, which):
        which.return_value = "/usr/bin/ffmpeg"

        with TemporaryDirectory() as tmp:
            service = RecordingService(directory=tmp)

            with self.assertRaisesRegex(
                RecordingError,
                "plain filename",
            ):
                service.start(filename="../video.mp4")

    @patch("betabox_robotics.vision.recording.shutil.which")
    @patch("betabox_robotics.vision.recording.threading.Thread")
    def test_start_adds_mp4_extension(
        self,
        thread,
        which,
    ):
        which.return_value = "/usr/bin/ffmpeg"
        thread.return_value = MagicMock()

        with TemporaryDirectory() as tmp:
            service = RecordingService(directory=tmp)

            path = service.start(filename="lesson")

            self.assertEqual(path.name, "lesson.mp4")

    @patch("betabox_robotics.vision.recording.shutil.which")
    @patch("betabox_robotics.vision.recording.Path.mkdir")
    def test_start_wraps_directory_error(
        self,
        mkdir,
        which,
    ):
        which.return_value = "/usr/bin/ffmpeg"
        mkdir.side_effect = OSError("permission denied")

        service = RecordingService(directory="/bad")

        with self.assertRaisesRegex(
            RecordingError,
            "recording directory is not writable",
        ):
            service.start()

    @patch.object(RecordingService, "_open_encoder")
    def test_first_frame_opens_encoder(self, open_encoder):
        service = RecordingService()

        frame = Frame.create(np.zeros((20, 30, 3), dtype=np.uint8))

        process = MagicMock()
        process.stdin = MagicMock()

        def fake_open_encoder(size, timestamp):
            service._process = process
            service._size = size
            service._start_timestamp = timestamp
            service._end_timestamp = timestamp

        open_encoder.side_effect = fake_open_encoder

        service._write_frame(frame)

        open_encoder.assert_called_once()
        process.stdin.write.assert_called_once()

    def test_frame_size_change_raises(self):
        service = RecordingService()

        service._size = (640, 480)

        process = MagicMock()
        process.stdin = MagicMock()

        service._process = process

        frame = Frame.create(np.zeros((720, 1280, 3), dtype=np.uint8))

        with self.assertRaisesRegex(
            RecordingError,
            "frame size changed",
        ):
            service._write_frame(frame)

    def test_broken_pipe_raises(self):
        service = RecordingService()

        process = MagicMock()
        process.stdin.write.side_effect = BrokenPipeError()

        stderr = MagicMock()
        stderr.read.return_value = b"encoder failed"

        process.stderr = stderr

        service._process = process
        service._size = (30, 20)

        frame = Frame.create(np.zeros((20, 30, 3), dtype=np.uint8))

        with self.assertRaisesRegex(
            RecordingError,
            "FFmpeg stopped accepting frames",
        ):
            service._write_frame(frame)

    @patch("betabox_robotics.vision.recording.subprocess.Popen")
    def test_open_encoder_wraps_popen_error(self, popen):
        popen.side_effect = OSError("boom")

        service = RecordingService()

        service._path = Path("/tmp/video.mp4")

        with self.assertRaisesRegex(
            RecordingError,
            "failed to start FFmpeg",
        ):
            service._open_encoder(
                (640, 480),
                1.0,
            )

    def test_overlay_is_used(self):
        overlay = MagicMock(spec=OverlayRenderer)
        overlay.draw_metadata.side_effect = lambda frame, metadata: frame

        bus = MagicMock(spec=MetadataBus)

        frame = Frame.create(np.zeros((20, 30, 3), dtype=np.uint8))

        metadata = Metadata(
            source="test",
            timestamp=frame.timestamp,
        )

        bus.latest.return_value = metadata

        service = RecordingService(
            metadata_bus=bus,
            overlay=overlay,
        )

        process = MagicMock()
        process.stdin = MagicMock()

        service._process = process
        service._size = (30, 20)

        service.enable_overlay("test")

        service._write_frame(frame)

        overlay.draw_metadata.assert_called_once()
        bus.latest.assert_called_once_with("test")


if __name__ == "__main__":
    unittest.main()
