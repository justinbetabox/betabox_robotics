import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import (
    OverlayError,
    OverlayRenderer,
)
from betabox_robotics.vision.recording import (
    Recording,
    RecordingError,
    RecordingService,
    _validate_directory,
    _validate_filename,
    _validate_filename_prefix,
    _validate_fps,
)


def create_test_frame(
    *,
    width: int = 20,
    height: int = 10,
    timestamp: float = 123.5,
) -> Frame:
    return Frame.create(
        np.zeros(
            (height, width, 3),
            dtype=np.uint8,
        ),
        timestamp=timestamp,
    )


def create_mock_process() -> MagicMock:
    process = MagicMock()
    process.stdin = MagicMock()
    process.stderr = MagicMock()
    process.stderr.read.return_value = b""
    process.wait.return_value = 0
    process.poll.return_value = None
    return process


class RecordingValidationTests(unittest.TestCase):
    def test_validate_directory(self) -> None:
        self.assertEqual(
            _validate_directory("recordings"),
            Path("recordings"),
        )

    def test_validate_directory_accepts_path(self) -> None:
        directory = Path("recordings")

        self.assertEqual(
            _validate_directory(directory),
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
                _validate_directory(value)

    def test_validate_fps(self) -> None:
        self.assertEqual(
            _validate_fps(20),
            20.0,
        )
        self.assertEqual(
            _validate_fps(20.5),
            20.5,
        )

    def test_validate_fps_rejects_invalid_type(self) -> None:
        for value in (
            True,
            "20",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "fps must be a number",
                ),
            ):
                _validate_fps(value)

    def test_validate_fps_rejects_non_finite_value(
        self,
    ) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be finite",
                ),
            ):
                _validate_fps(value)

    def test_validate_fps_rejects_non_positive_value(
        self,
    ) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be greater than 0",
                ),
            ):
                _validate_fps(value)

    def test_validate_filename(self) -> None:
        self.assertEqual(
            _validate_filename("  lesson.mp4  "),
            "lesson.mp4",
        )

    def test_validate_filename_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "filename must be a string",
        ):
            _validate_filename(123)

    def test_validate_filename_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "filename cannot be empty",
        ):
            _validate_filename(" ")

    def test_validate_filename_rejects_directory(
        self,
    ) -> None:
        for value in (
            "videos/lesson.mp4",
            "../lesson.mp4",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "filename must not contain a directory",
                ),
            ):
                _validate_filename(value)

    def test_validate_filename_prefix(self) -> None:
        self.assertEqual(
            _validate_filename_prefix("  lesson  "),
            "lesson",
        )

    def test_validate_filename_prefix_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "filename_prefix must be a string",
        ):
            _validate_filename_prefix(123)

    def test_validate_filename_prefix_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "filename_prefix cannot be empty",
        ):
            _validate_filename_prefix(" ")

    def test_validate_filename_prefix_rejects_directory(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "filename_prefix must not contain a directory",
        ):
            _validate_filename_prefix("videos/recording")


class RecordingDataModelTests(unittest.TestCase):
    def test_duration(self) -> None:
        recording = Recording(
            path=Path("test.mp4"),
            start_timestamp=10.0,
            end_timestamp=12.5,
            frame_count=50,
            fps=20.0,
        )

        self.assertEqual(
            recording.duration,
            2.5,
        )

    def test_duration_cannot_be_negative(self) -> None:
        recording = Recording(
            path=Path("test.mp4"),
            start_timestamp=12.5,
            end_timestamp=10.0,
            frame_count=0,
            fps=20.0,
        )

        self.assertEqual(
            recording.duration,
            0.0,
        )


class RecordingConfigurationTests(unittest.TestCase):
    def test_default_configuration(self) -> None:
        service = RecordingService()

        self.assertEqual(
            service.directory,
            Path("/tmp/betabox-video"),
        )
        self.assertEqual(
            service.fps,
            20.0,
        )
        self.assertEqual(
            service.filename_prefix,
            "recording",
        )
        self.assertIsNone(service.metadata_bus)
        self.assertIsInstance(
            service.overlay,
            OverlayRenderer,
        )
        self.assertFalse(service.is_recording())
        self.assertIsNone(service.last_error())

    def test_custom_configuration(self) -> None:
        metadata_bus = MetadataBus()
        overlay = OverlayRenderer()

        service = RecordingService(
            directory="videos",
            fps=15,
            filename_prefix="lesson",
            metadata_bus=metadata_bus,
            overlay=overlay,
        )

        self.assertEqual(
            service.directory,
            Path("videos"),
        )
        self.assertEqual(
            service.fps,
            15.0,
        )
        self.assertEqual(
            service.filename_prefix,
            "lesson",
        )
        self.assertIs(
            service.metadata_bus,
            metadata_bus,
        )
        self.assertIs(
            service.overlay,
            overlay,
        )

    def test_rejects_invalid_metadata_bus(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "metadata_bus must be a MetadataBus",
        ):
            RecordingService(
                metadata_bus=object(),  # type: ignore[arg-type]
            )

    def test_rejects_invalid_overlay(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "overlay must be an OverlayRenderer",
        ):
            RecordingService(
                overlay=object(),  # type: ignore[arg-type]
            )


class RecordingStartTests(unittest.TestCase):
    def test_start_requires_ffmpeg(self) -> None:
        service = RecordingService()

        with (
            patch(
                "betabox_robotics.vision.recording.shutil.which",
                return_value=None,
            ),
            self.assertRaisesRegex(
                RecordingError,
                "ffmpeg is not installed",
            ),
        ):
            service.start()

    def test_start_rejects_running_recording(self) -> None:
        service = RecordingService()

        with service._frame_condition:
            service._recording = True

        with self.assertRaisesRegex(
            RecordingError,
            "recording is already running",
        ):
            service.start()

    def test_start_creates_named_recording(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = RecordingService(directory=temp_dir)
            worker = MagicMock()

            with (
                patch(
                    "betabox_robotics.vision.recording.shutil.which",
                    return_value="/usr/bin/ffmpeg",
                ),
                patch(
                    "betabox_robotics.vision.recording.threading.Thread",
                    return_value=worker,
                ),
            ):
                path = service.start(filename="lesson")

            self.assertEqual(
                path,
                Path(temp_dir) / "lesson.mp4",
            )
            self.assertTrue(service.is_recording())
            self.assertIs(
                service._worker,
                worker,
            )
            worker.start.assert_called_once_with()

    def test_start_replaces_filename_extension(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = RecordingService(directory=temp_dir)
            worker = MagicMock()

            with (
                patch(
                    "betabox_robotics.vision.recording.shutil.which",
                    return_value="/usr/bin/ffmpeg",
                ),
                patch(
                    "betabox_robotics.vision.recording.threading.Thread",
                    return_value=worker,
                ),
            ):
                path = service.start(filename="lesson.avi")

            self.assertEqual(
                path.name,
                "lesson.mp4",
            )

    def test_start_generates_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = RecordingService(
                directory=temp_dir,
                filename_prefix="lesson",
            )
            worker = MagicMock()

            with (
                patch(
                    "betabox_robotics.vision.recording.shutil.which",
                    return_value="/usr/bin/ffmpeg",
                ),
                patch(
                    "betabox_robotics.vision.recording.strftime",
                    return_value="20260804_121500",
                ),
                patch(
                    "betabox_robotics.vision.recording.threading.Thread",
                    return_value=worker,
                ),
            ):
                path = service.start()

            self.assertEqual(
                path.name,
                "lesson_20260804_121500.mp4",
            )

    def test_start_wraps_directory_failure(self) -> None:
        service = RecordingService(
            directory="/unwritable",
        )

        with (
            patch(
                "betabox_robotics.vision.recording.shutil.which",
                return_value="/usr/bin/ffmpeg",
            ),
            patch(
                "betabox_robotics.vision.recording.Path.mkdir",
                side_effect=OSError("permission denied"),
            ),
            self.assertRaisesRegex(
                RecordingError,
                "recording directory is not writable",
            ),
        ):
            service.start()

    def test_start_rolls_back_when_worker_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = RecordingService(directory=temp_dir)
            worker = MagicMock()
            worker.start.side_effect = RuntimeError("thread failed")

            with (
                patch(
                    "betabox_robotics.vision.recording.shutil.which",
                    return_value="/usr/bin/ffmpeg",
                ),
                patch(
                    "betabox_robotics.vision.recording.threading.Thread",
                    return_value=worker,
                ),
                self.assertRaisesRegex(
                    RuntimeError,
                    "thread failed",
                ),
            ):
                service.start(filename="lesson.mp4")

            self.assertFalse(service.is_recording())
            self.assertIsNone(service._worker)
            self.assertIsNone(service._path)


class RecordingFrameTests(unittest.TestCase):
    def test_on_frame_requires_frame(self) -> None:
        service = RecordingService()

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            service.on_frame(
                object(),  # type: ignore[arg-type]
            )

    def test_on_frame_ignored_when_not_recording(
        self,
    ) -> None:
        service = RecordingService()
        frame = create_test_frame()

        service.on_frame(frame)

        self.assertIsNone(service._pending_frame)

    def test_on_frame_stores_latest_pending_frame(
        self,
    ) -> None:
        service = RecordingService()
        first = create_test_frame(timestamp=1.0)
        second = create_test_frame(timestamp=2.0)

        with service._frame_condition:
            service._recording = True

        service.on_frame(first)
        service.on_frame(second)

        self.assertIs(
            service._pending_frame,
            second,
        )

    def test_write_frame_requires_frame(self) -> None:
        service = RecordingService()

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            service._write_frame(
                object()  # type: ignore[arg-type]
            )

    def test_write_frame_requires_numpy_image(
        self,
    ) -> None:
        service = RecordingService()

        with self.assertRaisesRegex(
            TypeError,
            "frame image must be a NumPy array",
        ):
            service._write_frame(Frame.create(object()))

    def test_write_frame_requires_three_channels(
        self,
    ) -> None:
        service = RecordingService()

        for image in (
            np.zeros(
                (10, 10),
                dtype=np.uint8,
            ),
            np.zeros(
                (10, 10, 1),
                dtype=np.uint8,
            ),
            np.zeros(
                (10, 10, 4),
                dtype=np.uint8,
            ),
        ):
            with (
                self.subTest(shape=image.shape),
                self.assertRaisesRegex(
                    RecordingError,
                    "recording requires a 3-channel image",
                ),
            ):
                service._write_frame(Frame.create(image))

    def test_write_frame_opens_encoder_and_writes_bytes(
        self,
    ) -> None:
        service = RecordingService()
        service._path = Path("lesson.mp4")
        process = create_mock_process()

        with patch(
            "betabox_robotics.vision.recording.subprocess.Popen",
            return_value=process,
        ):
            service._write_frame(
                create_test_frame(
                    width=30,
                    height=20,
                    timestamp=10.0,
                )
            )

        self.assertEqual(
            service._size,
            (30, 20),
        )
        self.assertEqual(
            service._start_timestamp,
            10.0,
        )
        self.assertEqual(
            service._end_timestamp,
            10.0,
        )
        self.assertEqual(
            service._frame_count,
            1,
        )
        process.stdin.write.assert_called_once()

    def test_write_frame_rejects_size_change(
        self,
    ) -> None:
        service = RecordingService()
        service._process = create_mock_process()
        service._size = (20, 10)

        with self.assertRaisesRegex(
            RecordingError,
            "frame size changed during recording",
        ):
            service._write_frame(
                create_test_frame(
                    width=30,
                    height=10,
                )
            )

    def test_write_frame_wraps_color_conversion_failure(
        self,
    ) -> None:
        service = RecordingService()
        service._process = create_mock_process()
        service._size = (20, 10)

        with (
            patch(
                "betabox_robotics.vision.recording.cv2.cvtColor",
                side_effect=cv2.error("conversion failed"),
            ),
            self.assertRaisesRegex(
                RecordingError,
                "failed to prepare recording frame",
            ),
        ):
            service._write_frame(create_test_frame())

    def test_write_frame_wraps_broken_pipe(
        self,
    ) -> None:
        service = RecordingService()
        process = create_mock_process()
        process.stdin.write.side_effect = BrokenPipeError()
        process.stderr.read.return_value = b"encoder failed"

        service._process = process
        service._size = (20, 10)

        with self.assertRaisesRegex(
            RecordingError,
            ("FFmpeg stopped accepting frames: encoder failed"),
        ):
            service._write_frame(create_test_frame())

    def test_write_frame_applies_overlay(self) -> None:
        metadata_bus = MetadataBus()
        metadata = Metadata.create(
            "color",
            timestamp=123.5,
        )
        metadata_bus.publish(metadata)

        overlay = MagicMock(spec=OverlayRenderer)
        overlay.draw_metadata.return_value = create_test_frame(timestamp=123.5)

        service = RecordingService(
            metadata_bus=metadata_bus,
            overlay=overlay,
        )
        service.enable_overlay("color")
        service._process = create_mock_process()
        service._size = (20, 10)

        frame = create_test_frame(timestamp=123.5)
        service._write_frame(frame)

        overlay.draw_metadata.assert_called_once_with(
            frame,
            metadata,
        )

    def test_overlay_failure_is_ignored(self) -> None:
        metadata_bus = MetadataBus()
        metadata_bus.publish(Metadata.create("color"))

        overlay = MagicMock(spec=OverlayRenderer)
        overlay.draw_metadata.side_effect = OverlayError("failed")

        service = RecordingService(
            metadata_bus=metadata_bus,
            overlay=overlay,
        )
        service.enable_overlay("color")
        service._process = create_mock_process()
        service._size = (20, 10)

        service._write_frame(create_test_frame())

        self.assertEqual(
            service._frame_count,
            1,
        )


class RecordingOverlayTests(unittest.TestCase):
    def test_enable_overlay(self) -> None:
        service = RecordingService()

        service.enable_overlay("color")

        self.assertEqual(
            service.overlay_status(),
            {
                "enabled": True,
                "source": "color",
            },
        )

    def test_enable_overlay_without_source(self) -> None:
        service = RecordingService()

        service.enable_overlay()

        self.assertEqual(
            service.overlay_status(),
            {
                "enabled": True,
                "source": None,
            },
        )

    def test_enable_overlay_normalizes_source(self) -> None:
        service = RecordingService()

        service.enable_overlay("  color  ")

        self.assertEqual(
            service.overlay_source,
            "color",
        )

    def test_enable_overlay_rejects_invalid_source(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "source must be a string",
        ):
            RecordingService().enable_overlay(
                123  # type: ignore[arg-type]
            )

    def test_enable_overlay_rejects_empty_source(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "source cannot be empty",
        ):
            RecordingService().enable_overlay(" ")

    def test_disable_overlay(self) -> None:
        service = RecordingService()
        service.enable_overlay("color")

        service.disable_overlay()

        self.assertEqual(
            service.overlay_status(),
            {
                "enabled": False,
                "source": None,
            },
        )


class RecordingEncoderTests(unittest.TestCase):
    def test_open_encoder_requires_path(self) -> None:
        service = RecordingService()

        with self.assertRaisesRegex(
            RecordingError,
            "recording path has not been initialized",
        ):
            service._open_encoder(
                (640, 480),
                10.0,
            )

    def test_open_encoder_starts_ffmpeg(self) -> None:
        service = RecordingService(fps=15)
        service._path = Path("lesson.mp4")
        process = create_mock_process()

        with patch(
            "betabox_robotics.vision.recording.subprocess.Popen",
            return_value=process,
        ) as popen:
            service._open_encoder(
                (640, 480),
                10.0,
            )

        command = popen.call_args.args[0]

        self.assertIn(
            "640x480",
            command,
        )
        self.assertIn(
            "15.0",
            command,
        )
        self.assertEqual(
            command[-1],
            "lesson.mp4",
        )
        self.assertIs(
            service._process,
            process,
        )
        self.assertEqual(
            service._size,
            (640, 480),
        )
        self.assertEqual(
            service._start_timestamp,
            10.0,
        )

    def test_open_encoder_wraps_process_failure(
        self,
    ) -> None:
        service = RecordingService()
        service._path = Path("lesson.mp4")

        with (
            patch(
                "betabox_robotics.vision.recording.subprocess.Popen",
                side_effect=OSError("failed"),
            ),
            self.assertRaisesRegex(
                RecordingError,
                "failed to start FFmpeg",
            ),
        ):
            service._open_encoder(
                (640, 480),
                10.0,
            )

    def test_open_encoder_rejects_missing_stdin(
        self,
    ) -> None:
        service = RecordingService()
        service._path = Path("lesson.mp4")
        process = create_mock_process()
        process.stdin = None

        with (
            patch(
                "betabox_robotics.vision.recording.subprocess.Popen",
                return_value=process,
            ),
            self.assertRaisesRegex(
                RecordingError,
                "failed to open FFmpeg input pipe",
            ),
        ):
            service._open_encoder(
                (640, 480),
                10.0,
            )

        process.kill.assert_called_once_with()
        process.wait.assert_called_once_with()

    def test_abort_encoder(self) -> None:
        service = RecordingService()
        process = create_mock_process()
        service._process = process

        service._abort_encoder()

        self.assertIsNone(service._process)
        process.stdin.close.assert_called_once_with()
        process.kill.assert_called_once_with()
        process.wait.assert_called_once_with(
            timeout=5.0,
        )

    def test_abort_encoder_retries_after_timeout(
        self,
    ) -> None:
        service = RecordingService()
        process = create_mock_process()
        process.wait.side_effect = (
            subprocess.TimeoutExpired(
                cmd="ffmpeg",
                timeout=5.0,
            ),
            0,
        )
        service._process = process

        service._abort_encoder()

        self.assertEqual(
            process.kill.call_count,
            2,
        )
        self.assertEqual(
            process.wait.call_count,
            2,
        )


class RecordingStopTests(unittest.TestCase):
    def test_stop_rejects_inactive_recording(self) -> None:
        service = RecordingService()

        with self.assertRaisesRegex(
            RecordingError,
            "recording is not running",
        ):
            service.stop()

    def test_stop_returns_recording(self) -> None:
        service = RecordingService(fps=20)
        worker = MagicMock()
        worker.is_alive.return_value = False

        with service._lock:
            service._recording = True
            service._worker = worker
            service._path = Path("lesson.mp4")
            service._start_timestamp = 10.0
            service._end_timestamp = 12.5
            service._frame_count = 50

        recording = service.stop()

        self.assertEqual(
            recording.path,
            Path("lesson.mp4"),
        )
        self.assertEqual(
            recording.start_timestamp,
            10.0,
        )
        self.assertEqual(
            recording.end_timestamp,
            12.5,
        )
        self.assertEqual(
            recording.frame_count,
            50,
        )
        self.assertEqual(
            recording.fps,
            20.0,
        )
        worker.join.assert_called_once_with(
            timeout=5.0,
        )

    def test_stop_uses_start_timestamp_when_end_missing(
        self,
    ) -> None:
        service = RecordingService()
        worker = MagicMock()
        worker.is_alive.return_value = False

        with service._lock:
            service._recording = True
            service._worker = worker
            service._path = Path("lesson.mp4")
            service._start_timestamp = 0.0
            service._end_timestamp = None

        recording = service.stop()

        self.assertEqual(
            recording.start_timestamp,
            0.0,
        )
        self.assertEqual(
            recording.end_timestamp,
            0.0,
        )

    def test_stop_rejects_recording_without_frames(
        self,
    ) -> None:
        service = RecordingService()
        worker = MagicMock()
        worker.is_alive.return_value = False

        with service._lock:
            service._recording = True
            service._worker = worker
            service._path = Path("lesson.mp4")

        with self.assertRaisesRegex(
            RecordingError,
            "recording stopped before any frames were captured",
        ):
            service.stop()

    def test_stop_raises_worker_error(self) -> None:
        service = RecordingService()
        error = RecordingError("write failed")

        with service._lock:
            service._last_error = error

        with self.assertRaisesRegex(
            RecordingError,
            "recording failed: write failed",
        ) as context:
            service.stop()

        self.assertIs(
            context.exception.__cause__,
            error,
        )

    def test_stop_aborts_worker_after_first_timeout(
        self,
    ) -> None:
        service = RecordingService()
        worker = MagicMock()
        worker.is_alive.side_effect = (
            True,
            False,
        )

        with service._lock:
            service._recording = True
            service._worker = worker
            service._path = Path("lesson.mp4")
            service._start_timestamp = 1.0

        with patch.object(
            service,
            "_abort_encoder",
        ) as abort:
            service.stop()

        self.assertEqual(
            worker.join.call_count,
            2,
        )
        abort.assert_called_once_with()

    def test_stop_raises_when_worker_never_stops(
        self,
    ) -> None:
        service = RecordingService()
        worker = MagicMock()
        worker.is_alive.return_value = True

        with service._lock:
            service._recording = True
            service._worker = worker

        with (
            patch.object(
                service,
                "_abort_encoder",
            ),
            self.assertRaisesRegex(
                RecordingError,
                "recording worker did not stop within 10 seconds",
            ),
        ):
            service.stop()

    def test_stop_waits_for_ffmpeg(self) -> None:
        service = RecordingService()
        worker = MagicMock()
        worker.is_alive.return_value = False
        process = create_mock_process()

        with service._lock:
            service._recording = True
            service._worker = worker
            service._process = process
            service._path = Path("lesson.mp4")
            service._start_timestamp = 1.0
            service._end_timestamp = 2.0

        service.stop()

        process.stdin.close.assert_called_once_with()
        process.wait.assert_called_once_with(
            timeout=30.0,
        )

    def test_stop_wraps_ffmpeg_timeout(self) -> None:
        service = RecordingService()
        worker = MagicMock()
        worker.is_alive.return_value = False
        process = create_mock_process()
        process.wait.side_effect = (
            subprocess.TimeoutExpired(
                cmd="ffmpeg",
                timeout=30.0,
            ),
            0,
        )

        with service._lock:
            service._recording = True
            service._worker = worker
            service._process = process
            service._path = Path("lesson.mp4")
            service._start_timestamp = 1.0

        with self.assertRaisesRegex(
            RecordingError,
            "FFmpeg did not finish within 30 seconds",
        ):
            service.stop()

        process.kill.assert_called_once_with()

    def test_stop_reports_ffmpeg_failure(self) -> None:
        service = RecordingService()
        worker = MagicMock()
        worker.is_alive.return_value = False
        process = create_mock_process()
        process.wait.return_value = 1
        process.stderr.read.return_value = b"encoding failed"

        with service._lock:
            service._recording = True
            service._worker = worker
            service._process = process
            service._path = Path("lesson.mp4")
            service._start_timestamp = 1.0

        with self.assertRaisesRegex(
            RecordingError,
            "FFmpeg failed: encoding failed",
        ):
            service.stop()


class RecordingDataTests(unittest.TestCase):
    def test_stop_data_reads_and_removes_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lesson.mp4"
            path.write_bytes(b"recording-data")

            recording = Recording(
                path=path,
                start_timestamp=1.0,
                end_timestamp=2.0,
                frame_count=20,
                fps=20.0,
            )

            service = RecordingService()

            with patch.object(
                service,
                "stop",
                return_value=recording,
            ):
                result = service.stop_data()

            self.assertEqual(
                result.data,
                b"recording-data",
            )
            self.assertEqual(
                result.format,
                "mp4",
            )
            self.assertEqual(
                result.start_timestamp,
                1.0,
            )
            self.assertEqual(
                result.end_timestamp,
                2.0,
            )
            self.assertEqual(
                result.frame_count,
                20,
            )
            self.assertEqual(
                result.fps,
                20.0,
            )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
