from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import FrameSourceError
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.recording import (
    Recording,
    RecordingData,
    RecordingError,
)
from betabox_robotics.vision.service import (
    VisionService,
    VisionServiceConfig,
)
from betabox_robotics.vision.snapshot import (
    Snapshot,
    SnapshotData,
)
from betabox_robotics.vision.stream import StreamError


class VisionServiceConfigTests(unittest.TestCase):
    def test_default_configuration(self) -> None:
        config = VisionServiceConfig()

        self.assertEqual(
            config.host,
            "0.0.0.0",
        )
        self.assertEqual(
            config.port,
            8080,
        )
        self.assertEqual(
            config.fps,
            20,
        )

    def test_normalizes_host(self) -> None:
        config = VisionServiceConfig(
            host="  127.0.0.1  ",
        )

        self.assertEqual(
            config.host,
            "127.0.0.1",
        )

    def test_rejects_non_string_host(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "host must be a string",
        ):
            VisionServiceConfig(
                host=123,  # type: ignore[arg-type]
            )

    def test_rejects_empty_host(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "host cannot be empty",
        ):
            VisionServiceConfig(
                host=" ",
            )

    def test_rejects_non_integer_port(self) -> None:
        for value in (
            True,
            8080.0,
            "8080",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "port must be an integer",
                ),
            ):
                VisionServiceConfig(
                    port=value,  # type: ignore[arg-type]
                )

    def test_rejects_out_of_range_port(self) -> None:
        for value in (
            0,
            -1,
            65536,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "port must be between 1 and 65535",
                ),
            ):
                VisionServiceConfig(
                    port=value,
                )

    def test_rejects_non_integer_fps(self) -> None:
        for value in (
            True,
            20.0,
            "20",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "fps must be an integer",
                ),
            ):
                VisionServiceConfig(
                    fps=value,  # type: ignore[arg-type]
                )

    def test_rejects_non_positive_fps(self) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be greater than zero",
                ),
            ):
                VisionServiceConfig(
                    fps=value,
                )


class VisionServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.frame_source = MagicMock()
        self.metadata_bus = MagicMock()
        self.overlay = MagicMock()
        self.detection = MagicMock()
        self.recording = MagicMock()
        self.streamer = MagicMock()
        self.snapshot = MagicMock()
        self.server = MagicMock()

        self.recording.is_recording.return_value = False
        self.recording.overlay_status.return_value = {
            "enabled": False,
            "source": None,
        }
        self.streamer.statistics.return_value = {
            "running": False,
            "clients": 0,
            "overlay": {
                "enabled": False,
                "source": None,
            },
            "frames_received": 0,
            "has_frame": False,
        }
        self.streamer.overlay_status.return_value = {
            "enabled": False,
            "source": None,
        }
        self.frame_source.statistics.return_value = {
            "running": False,
        }
        self.metadata_bus.all_latest.return_value = {}
        self.detection.names.return_value = [
            "color",
            "face",
            "objects",
        ]
        self.detection.is_enabled.side_effect = lambda name: name == "color"

        self.patchers = (
            patch(
                "betabox_robotics.vision.service.FrameSource",
                return_value=self.frame_source,
            ),
            patch(
                "betabox_robotics.vision.service.MetadataBus",
                return_value=self.metadata_bus,
            ),
            patch(
                "betabox_robotics.vision.service.OverlayRenderer",
                return_value=self.overlay,
            ),
            patch(
                "betabox_robotics.vision.service.DetectionManager",
                return_value=self.detection,
            ),
            patch(
                "betabox_robotics.vision.service.RecordingService",
                return_value=self.recording,
            ),
            patch(
                "betabox_robotics.vision.service.WebRTCStreamer",
                return_value=self.streamer,
            ),
            patch(
                "betabox_robotics.vision.service.SnapshotService",
                return_value=self.snapshot,
            ),
            patch(
                "betabox_robotics.vision.service.WebRTCSignalingServer",
                return_value=self.server,
            ),
        )

        self.mocks = [patcher.start() for patcher in self.patchers]

        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()

    def create_service(
        self,
        config: VisionServiceConfig | None = None,
    ) -> VisionService:
        return VisionService(config)


class VisionServiceConstructionTests(VisionServiceTestCase):
    def test_rejects_invalid_config(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "config must be a VisionServiceConfig",
        ):
            VisionService(
                object(),  # type: ignore[arg-type]
            )

    def test_constructs_default_service(self) -> None:
        service = self.create_service()

        self.assertEqual(
            service.config,
            VisionServiceConfig(),
        )
        self.assertIs(
            service.frame_source,
            self.frame_source,
        )
        self.assertIs(
            service.metadata_bus,
            self.metadata_bus,
        )
        self.assertIs(
            service.overlay,
            self.overlay,
        )
        self.assertIs(
            service.detection,
            self.detection,
        )
        self.assertIs(
            service.recording,
            self.recording,
        )
        self.assertIs(
            service.streamer,
            self.streamer,
        )
        self.assertIs(
            service.snapshot,
            self.snapshot,
        )
        self.assertIs(
            service.server,
            self.server,
        )
        self.assertFalse(service._running)

    def test_constructs_subsystems_from_config(self) -> None:
        config = VisionServiceConfig(
            host="127.0.0.1",
            port=9000,
            fps=15,
        )

        service = self.create_service(config)

        self.assertIs(
            service.config,
            config,
        )

        self.mocks[0].assert_called_once_with(
            fps=15,
        )
        self.mocks[1].assert_called_once_with()
        self.mocks[2].assert_called_once_with()
        self.mocks[3].assert_called_once_with(
            self.metadata_bus,
        )
        self.mocks[4].assert_called_once_with(
            fps=15,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )
        self.mocks[5].assert_called_once_with(
            fps=15,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )
        self.mocks[6].assert_called_once_with(
            self.frame_source,
        )
        self.mocks[7].assert_called_once_with(
            service,
            host="127.0.0.1",
            port=9000,
        )

    def test_registers_frame_consumers(self) -> None:
        self.create_service()

        self.assertEqual(
            self.frame_source.register_consumer.call_args_list,
            [
                call(self.detection),
                call(self.recording),
                call(self.streamer),
            ],
        )


class VisionServiceLifecycleTests(VisionServiceTestCase):
    def test_start_starts_pipeline(self) -> None:
        service = self.create_service()

        service.start()

        self.frame_source.start.assert_called_once_with()
        self.streamer.start.assert_called_once_with()
        self.assertTrue(service._running)

    def test_start_is_idempotent(self) -> None:
        service = self.create_service()

        service.start()
        service.start()

        self.frame_source.start.assert_called_once_with()
        self.streamer.start.assert_called_once_with()

    def test_start_rolls_back_frame_source_on_stream_error(
        self,
    ) -> None:
        service = self.create_service()
        failure = StreamError("stream startup failed")
        self.streamer.start.side_effect = failure

        with self.assertRaisesRegex(
            StreamError,
            "stream startup failed",
        ):
            service.start()

        self.frame_source.start.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(service._running)

    def test_start_preserves_stream_error_when_rollback_fails(
        self,
    ) -> None:
        service = self.create_service()
        stream_failure = StreamError("stream startup failed")

        self.streamer.start.side_effect = stream_failure
        self.frame_source.stop.side_effect = FrameSourceError("camera rollback failed")

        with self.assertRaisesRegex(
            StreamError,
            "stream startup failed",
        ) as context:
            service.start()

        self.assertIs(
            context.exception,
            stream_failure,
        )
        self.assertFalse(service._running)

    def test_run_starts_service_and_runs_server(
        self,
    ) -> None:
        service = self.create_service()

        service.run()

        self.frame_source.start.assert_called_once_with()
        self.streamer.start.assert_called_once_with()
        self.server.run.assert_called_once_with()
        self.assertTrue(service._running)

    def test_stop_is_noop_when_not_running(self) -> None:
        service = self.create_service()

        service.stop()

        self.streamer.stop.assert_not_called()
        self.recording.stop.assert_not_called()
        self.frame_source.stop.assert_not_called()

    def test_stop_stops_pipeline(self) -> None:
        service = self.create_service()
        service._running = True

        service.stop()

        self.streamer.stop.assert_called_once_with()
        self.recording.stop.assert_not_called()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(service._running)

    def test_stop_finishes_and_removes_active_recording(
        self,
    ) -> None:
        service = self.create_service()
        service._running = True
        self.recording.is_recording.return_value = True

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unfinished.mp4"
            path.write_bytes(b"video")

            recording = Recording(
                path=path,
                start_timestamp=10.0,
                end_timestamp=12.0,
                frame_count=40,
                fps=20.0,
            )
            self.recording.stop.return_value = recording

            service.stop()

            self.assertFalse(path.exists())

        self.recording.stop.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(service._running)

    def test_stop_ignores_missing_recording_file(
        self,
    ) -> None:
        service = self.create_service()
        service._running = True
        self.recording.is_recording.return_value = True

        recording = Recording(
            path=Path("/tmp/does-not-exist.mp4"),
            start_timestamp=10.0,
            end_timestamp=12.0,
            frame_count=40,
            fps=20.0,
        )
        self.recording.stop.return_value = recording

        service.stop()

        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(service._running)

    def test_stop_raises_recording_error_after_cleanup(
        self,
    ) -> None:
        service = self.create_service()
        service._running = True
        self.recording.is_recording.return_value = True

        failure = RecordingError("recording failed")
        self.recording.stop.side_effect = failure

        with self.assertRaisesRegex(
            RecordingError,
            "recording failed",
        ):
            service.stop()

        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(service._running)

    def test_stop_raises_stream_error_after_cleanup(
        self,
    ) -> None:
        service = self.create_service()
        service._running = True

        failure = StreamError("stream shutdown failed")
        self.streamer.stop.side_effect = failure

        with self.assertRaisesRegex(
            StreamError,
            "stream shutdown failed",
        ):
            service.stop()

        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(service._running)

    def test_stop_raises_frame_source_error(
        self,
    ) -> None:
        service = self.create_service()
        service._running = True

        failure = FrameSourceError("camera shutdown failed")
        self.frame_source.stop.side_effect = failure

        with self.assertRaisesRegex(
            FrameSourceError,
            "camera shutdown failed",
        ):
            service.stop()

        self.assertFalse(service._running)

    def test_stop_preserves_first_shutdown_error(
        self,
    ) -> None:
        service = self.create_service()
        service._running = True
        self.recording.is_recording.return_value = True

        stream_failure = StreamError("stream failed")
        recording_failure = RecordingError("recording failed")
        frame_failure = FrameSourceError("camera failed")

        self.streamer.stop.side_effect = stream_failure
        self.recording.stop.side_effect = recording_failure
        self.frame_source.stop.side_effect = frame_failure

        with self.assertRaisesRegex(
            StreamError,
            "stream failed",
        ) as context:
            service.stop()

        self.assertIs(
            context.exception,
            stream_failure,
        )
        self.recording.stop.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(service._running)

    def test_close_delegates_to_stop(self) -> None:
        service = self.create_service()

        with patch.object(
            service,
            "stop",
        ) as stop:
            service.close()

        stop.assert_called_once_with()


class VisionServiceSnapshotTests(VisionServiceTestCase):
    def test_capture_snapshot_without_overlay(self) -> None:
        service = self.create_service()

        expected = Snapshot(
            path=Path("picture.png"),
            timestamp=123.5,
            format="png",
        )
        self.snapshot.capture.return_value = expected

        result = service.capture_snapshot(
            filename="picture.png",
            directory="pictures",
            image_format="png",
        )

        self.assertIs(
            result,
            expected,
        )
        self.snapshot.capture.assert_called_once_with(
            filename="picture.png",
            directory="pictures",
            image_format="png",
        )
        self.frame_source.latest_frame.assert_not_called()
        self.overlay.draw_metadata.assert_not_called()

    def test_capture_snapshot_with_overlay(self) -> None:
        service = self.create_service()

        frame = Frame.create(
            object(),
            timestamp=123.5,
        )
        rendered = Frame.create(
            object(),
            timestamp=123.5,
        )
        metadata = Metadata.create(
            "color",
            timestamp=123.5,
        )
        expected = Snapshot(
            path=Path("picture.jpg"),
            timestamp=123.5,
            format="jpg",
        )

        self.frame_source.latest_frame.return_value = frame
        self.metadata_bus.latest.return_value = metadata
        self.overlay.draw_metadata.return_value = rendered
        self.snapshot.capture_frame.return_value = expected

        result = service.capture_snapshot(
            filename="picture.jpg",
            directory="pictures",
            image_format="jpg",
            overlay=True,
            source="color",
        )

        self.assertIs(
            result,
            expected,
        )
        self.metadata_bus.latest.assert_called_once_with("color")
        self.overlay.draw_metadata.assert_called_once_with(
            frame,
            metadata,
        )
        self.snapshot.capture_frame.assert_called_once_with(
            rendered,
            filename="picture.jpg",
            directory="pictures",
            image_format="jpg",
        )

    def test_capture_snapshot_with_overlay_and_no_metadata(
        self,
    ) -> None:
        service = self.create_service()

        frame = Frame.create(
            object(),
            timestamp=123.5,
        )
        expected = Snapshot(
            path=Path("picture.jpg"),
            timestamp=123.5,
            format="jpg",
        )

        self.frame_source.latest_frame.return_value = frame
        self.metadata_bus.latest.return_value = None
        self.snapshot.capture_frame.return_value = expected

        result = service.capture_snapshot(
            overlay=True,
            source="color",
        )

        self.assertIs(
            result,
            expected,
        )
        self.overlay.draw_metadata.assert_not_called()
        self.snapshot.capture_frame.assert_called_once_with(
            frame,
            filename=None,
            directory=None,
            image_format=None,
        )

    def test_capture_snapshot_data_without_overlay(
        self,
    ) -> None:
        service = self.create_service()

        expected = SnapshotData(
            data=b"image",
            timestamp=123.5,
            format="png",
        )
        self.snapshot.capture_data.return_value = expected

        result = service.capture_snapshot_data(
            image_format="png",
        )

        self.assertIs(
            result,
            expected,
        )
        self.snapshot.capture_data.assert_called_once_with(
            image_format="png",
        )

    def test_capture_snapshot_data_with_overlay(
        self,
    ) -> None:
        service = self.create_service()

        frame = Frame.create(
            object(),
            timestamp=123.5,
        )
        rendered = Frame.create(
            object(),
            timestamp=123.5,
        )
        metadata = Metadata.create(
            "face",
            timestamp=123.5,
        )
        expected = SnapshotData(
            data=b"image",
            timestamp=123.5,
            format="jpg",
        )

        self.frame_source.latest_frame.return_value = frame
        self.metadata_bus.latest.return_value = metadata
        self.overlay.draw_metadata.return_value = rendered
        self.snapshot.capture_frame_data.return_value = expected

        result = service.capture_snapshot_data(
            overlay=True,
            source="face",
            image_format="jpeg",
        )

        self.assertIs(
            result,
            expected,
        )
        self.overlay.draw_metadata.assert_called_once_with(
            frame,
            metadata,
        )
        self.snapshot.capture_frame_data.assert_called_once_with(
            rendered,
            image_format="jpeg",
        )


class VisionServiceRecordingTests(VisionServiceTestCase):
    def test_start_recording_without_overlay(self) -> None:
        service = self.create_service()
        expected = Path("lesson.mp4")
        self.recording.start.return_value = expected

        result = service.start_recording(
            filename="lesson.mp4",
        )

        self.assertEqual(
            result,
            expected,
        )
        self.recording.disable_overlay.assert_called_once_with()
        self.recording.enable_overlay.assert_not_called()
        self.recording.start.assert_called_once_with(
            filename="lesson.mp4",
        )

    def test_start_recording_with_overlay(self) -> None:
        service = self.create_service()
        expected = Path("lesson.mp4")
        self.recording.start.return_value = expected

        result = service.start_recording(
            filename="lesson.mp4",
            overlay=True,
            source="color",
        )

        self.assertEqual(
            result,
            expected,
        )
        self.recording.enable_overlay.assert_called_once_with("color")
        self.recording.disable_overlay.assert_not_called()
        self.recording.start.assert_called_once_with(
            filename="lesson.mp4",
        )

    def test_stop_recording(self) -> None:
        service = self.create_service()

        expected = Recording(
            path=Path("lesson.mp4"),
            start_timestamp=10.0,
            end_timestamp=12.0,
            frame_count=40,
            fps=20.0,
        )
        self.recording.stop.return_value = expected

        self.assertIs(
            service.stop_recording(),
            expected,
        )
        self.recording.stop.assert_called_once_with()

    def test_stop_recording_data(self) -> None:
        service = self.create_service()

        expected = RecordingData(
            data=b"video",
            format="mp4",
            start_timestamp=10.0,
            end_timestamp=12.0,
            frame_count=40,
            fps=20.0,
        )
        self.recording.stop_data.return_value = expected

        self.assertIs(
            service.stop_recording_data(),
            expected,
        )
        self.recording.stop_data.assert_called_once_with()


class VisionServiceDetectionTests(VisionServiceTestCase):
    def test_enable_color_detection(self) -> None:
        service = self.create_service()

        custom_ranges = {
            "team_marker": (
                (
                    (10, 100, 100),
                    (20, 255, 255),
                ),
            ),
        }

        service.enable_color_detection(
            [
                "red",
                "team_marker",
            ],
            custom_ranges=custom_ranges,
            min_area=25,
        )

        self.detection.enable_color.assert_called_once_with(
            [
                "red",
                "team_marker",
            ],
            custom_ranges=custom_ranges,
            min_area=25,
        )

    def test_enable_detection(self) -> None:
        service = self.create_service()

        service.enable_detection("face")

        self.detection.enable.assert_called_once_with("face")

    def test_disable_detection(self) -> None:
        service = self.create_service()

        service.disable_detection("face")

        self.detection.disable.assert_called_once_with("face")

    def test_detection_names(self) -> None:
        service = self.create_service()

        self.assertEqual(
            service.detection_names(),
            [
                "color",
                "face",
                "objects",
            ],
        )

    def test_detection_status(self) -> None:
        service = self.create_service()

        self.assertEqual(
            service.detection_status(),
            {
                "color": True,
                "face": False,
                "objects": False,
            },
        )

    def test_latest_metadata(self) -> None:
        service = self.create_service()
        expected = Metadata.create("color")
        self.metadata_bus.latest.return_value = expected

        result = service.latest_metadata("color")

        self.assertIs(
            result,
            expected,
        )
        self.metadata_bus.latest.assert_called_once_with("color")


class VisionServiceOverlayTests(VisionServiceTestCase):
    def test_enable_stream_overlay(self) -> None:
        service = self.create_service()

        service.enable_stream_overlay("color")

        self.streamer.enable_overlay.assert_called_once_with("color")

    def test_disable_stream_overlay(self) -> None:
        service = self.create_service()

        service.disable_stream_overlay()

        self.streamer.disable_overlay.assert_called_once_with()

    def test_stream_overlay_status(self) -> None:
        service = self.create_service()
        expected = {
            "enabled": True,
            "source": "face",
        }
        self.streamer.overlay_status.return_value = expected

        self.assertIs(
            service.stream_overlay_status(),
            expected,
        )

    def test_enable_recording_overlay(self) -> None:
        service = self.create_service()

        service.enable_recording_overlay("color")

        self.recording.enable_overlay.assert_called_once_with("color")

    def test_disable_recording_overlay(self) -> None:
        service = self.create_service()

        service.disable_recording_overlay()

        self.recording.disable_overlay.assert_called_once_with()

    def test_recording_overlay_status(self) -> None:
        service = self.create_service()
        expected = {
            "enabled": True,
            "source": "color",
        }
        self.recording.overlay_status.return_value = expected

        self.assertIs(
            service.recording_overlay_status(),
            expected,
        )


class VisionServiceStatisticsTests(VisionServiceTestCase):
    def test_statistics(self) -> None:
        service = self.create_service()
        service._running = True

        camera_stats = {
            "running": True,
            "phase": "running",
        }
        stream_stats = {
            "running": True,
            "clients": 2,
            "overlay": {
                "enabled": True,
                "source": "color",
            },
            "frames_received": 100,
            "has_frame": True,
        }
        recording_overlay = {
            "enabled": False,
            "source": None,
        }

        self.frame_source.statistics.return_value = camera_stats
        self.streamer.statistics.return_value = stream_stats
        self.recording.is_recording.return_value = True
        self.recording.overlay_status.return_value = recording_overlay
        self.metadata_bus.all_latest.return_value = {
            "color": Metadata.create("color"),
            "face": Metadata.create("face"),
        }

        result = service.statistics()

        self.assertEqual(
            result,
            {
                "running": True,
                "camera": camera_stats,
                "streaming": stream_stats,
                "recording": {
                    "active": True,
                    "overlay": recording_overlay,
                },
                "detection": {
                    "detectors": {
                        "color": True,
                        "face": False,
                        "objects": False,
                    },
                    "metadata_sources": [
                        "color",
                        "face",
                    ],
                },
                "server": {
                    "host": "0.0.0.0",
                    "port": 8080,
                    "fps": 20,
                },
            },
        )


class VisionServiceContextManagerTests(VisionServiceTestCase):
    def test_context_manager_starts_and_stops(
        self,
    ) -> None:
        service = self.create_service()

        with (
            patch.object(
                service,
                "start",
            ) as start,
            patch.object(
                service,
                "stop",
            ) as stop,
            service as entered,
        ):
            self.assertIs(
                entered,
                service,
            )

        start.assert_called_once_with()
        stop.assert_called_once_with()

    def test_context_manager_stops_after_exception(
        self,
    ) -> None:
        service = self.create_service()

        with (
            patch.object(
                service,
                "start",
            ),
            patch.object(
                service,
                "stop",
            ) as stop,
            self.assertRaisesRegex(
                RuntimeError,
                "boom",
            ),
            service,
        ):
            raise RuntimeError("boom")

        stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
