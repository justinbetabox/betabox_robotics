import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.recording import Recording, RecordingData
from betabox_robotics.vision.service import (
    VisionService,
    VisionServiceConfig,
)
from betabox_robotics.vision.snapshot import Snapshot, SnapshotData


class VisionServiceConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = VisionServiceConfig()

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.fps, 20)

    def test_custom_values(self) -> None:
        config = VisionServiceConfig(
            host="127.0.0.1",
            port=9000,
            fps=15,
        )

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 9000)
        self.assertEqual(config.fps, 15)

    def test_empty_host_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "host cannot be empty",
        ):
            VisionServiceConfig(host="   ")

    def test_invalid_port_is_rejected(self) -> None:
        for port in (0, -1, 65536):
            with (
                self.subTest(port=port),
                self.assertRaisesRegex(
                    ValueError,
                    "port must be between 1 and 65535",
                ),
            ):
                VisionServiceConfig(port=port)

    def test_invalid_fps_is_rejected(self) -> None:
        for fps in (0, -1):
            with (
                self.subTest(fps=fps),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be greater than zero",
                ),
            ):
                VisionServiceConfig(fps=fps)


class VisionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame_source = MagicMock()
        self.metadata_bus = MagicMock()
        self.overlay = MagicMock()
        self.detection = MagicMock()
        self.recording = MagicMock()
        self.streamer = MagicMock()
        self.snapshot = MagicMock()
        self.server = MagicMock()

        patchers = [
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
        ]

        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.config = VisionServiceConfig(
            host="127.0.0.1",
            port=9000,
            fps=15,
        )
        self.service = VisionService(self.config)

    def test_constructs_components_with_shared_dependencies(self) -> None:
        from betabox_robotics.vision import service as service_module

        service_module.FrameSource.assert_called_once_with(
            fps=15,
        )
        service_module.DetectionManager.assert_called_once_with(
            self.metadata_bus,
        )
        service_module.RecordingService.assert_called_once_with(
            fps=15,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )
        service_module.WebRTCStreamer.assert_called_once_with(
            fps=15,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )
        service_module.SnapshotService.assert_called_once_with(
            self.frame_source,
        )
        service_module.WebRTCSignalingServer.assert_called_once_with(
            self.service,
            host="127.0.0.1",
            port=9000,
        )

    def test_registers_all_frame_consumers(self) -> None:
        self.assertEqual(
            self.frame_source.register_consumer.call_args_list,
            [
                call(self.detection),
                call(self.recording),
                call(self.streamer),
            ],
        )

    def test_start_starts_pipeline(self) -> None:
        self.service.start()

        self.frame_source.start.assert_called_once_with()
        self.streamer.start.assert_called_once_with()
        self.assertTrue(self.service._running)

    def test_start_is_idempotent(self) -> None:
        self.service.start()
        self.service.start()

        self.frame_source.start.assert_called_once_with()
        self.streamer.start.assert_called_once_with()

    def test_start_rolls_back_frame_source_when_streamer_fails(self) -> None:
        self.streamer.start.side_effect = RuntimeError("streamer failed")

        with self.assertRaisesRegex(
            RuntimeError,
            "streamer failed",
        ):
            self.service.start()

        self.frame_source.start.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(self.service._running)

    def test_run_starts_service_then_runs_server(self) -> None:
        with patch.object(
            self.service,
            "start",
        ) as start:
            self.service.run()

        start.assert_called_once_with()
        self.server.run.assert_called_once_with()

    def test_stop_stops_streamer_and_frame_source(self) -> None:
        self.service._running = True
        self.recording.is_recording.return_value = False

        self.service.stop()

        self.streamer.stop.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(self.service._running)

    def test_stop_is_idempotent(self) -> None:
        self.service.stop()

        self.streamer.stop.assert_not_called()
        self.frame_source.stop.assert_not_called()

    def test_stop_removes_unfinished_recording(self) -> None:
        path = MagicMock(spec=Path)

        recording = Recording(
            path=path,
            start_timestamp=1.0,
            end_timestamp=2.0,
            frame_count=20,
            fps=20.0,
        )

        self.service._running = True
        self.recording.is_recording.return_value = True
        self.recording.stop.return_value = recording

        self.service.stop()

        self.recording.stop.assert_called_once_with()
        path.unlink.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(self.service._running)

    def test_stop_ignores_missing_recording_file(self) -> None:
        path = MagicMock(spec=Path)
        path.unlink.side_effect = FileNotFoundError

        recording = Recording(
            path=path,
            start_timestamp=1.0,
            end_timestamp=2.0,
            frame_count=20,
            fps=20.0,
        )

        self.service._running = True
        self.recording.is_recording.return_value = True
        self.recording.stop.return_value = recording

        self.service.stop()

        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(self.service._running)

    def test_stop_still_stops_frame_source_when_recording_stop_fails(
        self,
    ) -> None:
        self.service._running = True
        self.recording.is_recording.return_value = True
        self.recording.stop.side_effect = RuntimeError("recording failed")

        with self.assertRaisesRegex(
            RuntimeError,
            "recording failed",
        ):
            self.service.stop()

        self.streamer.stop.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(self.service._running)

    def test_stop_still_stops_frame_source_when_unlink_fails(
        self,
    ) -> None:
        path = MagicMock(spec=Path)
        path.unlink.side_effect = OSError("unlink failed")

        recording = Recording(
            path=path,
            start_timestamp=1.0,
            end_timestamp=2.0,
            frame_count=20,
            fps=20.0,
        )

        self.service._running = True
        self.recording.is_recording.return_value = True
        self.recording.stop.return_value = recording

        with self.assertRaisesRegex(
            OSError,
            "unlink failed",
        ):
            self.service.stop()

        self.frame_source.stop.assert_called_once_with()
        self.assertFalse(self.service._running)

    def test_capture_snapshot_without_overlay_delegates(self) -> None:
        expected = MagicMock(spec=Snapshot)
        self.snapshot.capture.return_value = expected

        result = self.service.capture_snapshot(
            filename="photo.jpg",
        )

        self.assertIs(result, expected)
        self.snapshot.capture.assert_called_once_with(
            filename="photo.jpg",
        )
        self.frame_source.latest_frame.assert_not_called()

    def test_capture_snapshot_with_overlay_uses_selected_frame(
        self,
    ) -> None:
        frame = Frame.create(object())
        annotated = Frame.create(object())
        metadata = Metadata.create(
            "face",
            timestamp=frame.timestamp,
        )
        expected = MagicMock(spec=Snapshot)

        self.frame_source.latest_frame.return_value = frame
        self.metadata_bus.latest.return_value = metadata
        self.overlay.draw_metadata.return_value = annotated
        self.snapshot.capture_frame.return_value = expected

        result = self.service.capture_snapshot(
            overlay=True,
            source="face",
            filename="photo.jpg",
        )

        self.assertIs(result, expected)
        self.metadata_bus.latest.assert_called_once_with("face")
        self.overlay.draw_metadata.assert_called_once_with(
            frame,
            metadata,
        )
        self.snapshot.capture_frame.assert_called_once_with(
            annotated,
            filename="photo.jpg",
        )

    def test_capture_snapshot_without_metadata_uses_same_frame(
        self,
    ) -> None:
        frame = Frame.create(object())
        expected = MagicMock(spec=Snapshot)

        self.frame_source.latest_frame.return_value = frame
        self.metadata_bus.latest.return_value = None
        self.snapshot.capture_frame.return_value = expected

        result = self.service.capture_snapshot(
            overlay=True,
            source="face",
            filename="photo.jpg",
        )

        self.assertIs(result, expected)
        self.snapshot.capture.assert_not_called()
        self.snapshot.capture_frame.assert_called_once_with(
            frame,
            filename="photo.jpg",
        )
        self.overlay.draw_metadata.assert_not_called()

    def test_capture_snapshot_data_without_overlay_delegates(
        self,
    ) -> None:
        expected = MagicMock(spec=SnapshotData)
        self.snapshot.capture_data.return_value = expected

        result = self.service.capture_snapshot_data(
            image_format="png",
        )

        self.assertIs(result, expected)
        self.snapshot.capture_data.assert_called_once_with(
            image_format="png",
        )

    def test_capture_snapshot_data_with_overlay(self) -> None:
        frame = Frame.create(object())
        annotated = Frame.create(object())
        metadata = Metadata.create(
            "face",
            timestamp=frame.timestamp,
        )
        expected = MagicMock(spec=SnapshotData)

        self.frame_source.latest_frame.return_value = frame
        self.metadata_bus.latest.return_value = metadata
        self.overlay.draw_metadata.return_value = annotated
        self.snapshot.capture_frame_data.return_value = expected

        result = self.service.capture_snapshot_data(
            overlay=True,
            source="face",
            image_format="jpg",
        )

        self.assertIs(result, expected)
        self.overlay.draw_metadata.assert_called_once_with(
            frame,
            metadata,
        )
        self.snapshot.capture_frame_data.assert_called_once_with(
            annotated,
            image_format="jpg",
        )

    def test_start_recording_enables_requested_overlay(self) -> None:
        path = Path("/tmp/video.mp4")
        self.recording.start.return_value = path

        result = self.service.start_recording(
            filename="video.mp4",
            overlay=True,
            source="face",
        )

        self.assertEqual(result, path)
        self.recording.enable_overlay.assert_called_once_with("face")
        self.recording.disable_overlay.assert_not_called()
        self.recording.start.assert_called_once_with(
            filename="video.mp4",
        )

    def test_start_recording_disables_overlay_when_not_requested(
        self,
    ) -> None:
        self.service.start_recording(
            filename="video.mp4",
            overlay=False,
        )

        self.recording.disable_overlay.assert_called_once_with()
        self.recording.enable_overlay.assert_not_called()

    def test_recording_stop_methods_delegate(self) -> None:
        recording = MagicMock(spec=Recording)
        recording_data = MagicMock(spec=RecordingData)

        self.recording.stop.return_value = recording
        self.recording.stop_data.return_value = recording_data

        self.assertIs(
            self.service.stop_recording(),
            recording,
        )
        self.assertIs(
            self.service.stop_recording_data(),
            recording_data,
        )

    def test_detection_methods_delegate(self) -> None:
        self.detection.names.return_value = [
            "color",
            "face",
        ]
        self.detection.is_enabled.side_effect = lambda name: name == "color"

        self.service.enable_detection("face")
        self.service.disable_detection("color")

        self.assertEqual(
            self.service.detection_names(),
            [
                "color",
                "face",
            ],
        )
        self.assertEqual(
            self.service.detection_status(),
            {
                "color": True,
                "face": False,
            },
        )

        self.detection.enable.assert_called_once_with("face")
        self.detection.disable.assert_called_once_with("color")

    def test_stream_overlay_methods_delegate(self) -> None:
        status = {
            "enabled": True,
            "source": "face",
        }
        self.streamer.overlay_status.return_value = status

        self.service.enable_stream_overlay("face")
        self.service.disable_stream_overlay()

        self.assertEqual(
            self.service.stream_overlay_status(),
            status,
        )

        self.streamer.enable_overlay.assert_called_once_with("face")
        self.streamer.disable_overlay.assert_called_once_with()

    def test_recording_overlay_methods_delegate(self) -> None:
        status = {
            "enabled": True,
            "source": "face",
        }
        self.recording.overlay_status.return_value = status

        self.service.enable_recording_overlay("face")
        self.service.disable_recording_overlay()

        self.assertEqual(
            self.service.recording_overlay_status(),
            status,
        )

        self.recording.enable_overlay.assert_called_once_with("face")
        self.recording.disable_overlay.assert_called_once_with()

    def test_enable_color_detection_delegates_configuration(
        self,
    ) -> None:
        self.service.enable_color_detection(
            ["red", "green", "blue"],
            min_area=275,
        )

        self.detection.enable_color.assert_called_once_with(
            ["red", "green", "blue"],
            min_area=275,
        )

    def test_enable_color_detection_allows_current_configuration(
        self,
    ) -> None:
        self.service.enable_color_detection()

        self.detection.enable_color.assert_called_once_with(
            None,
            min_area=None,
        )

    def test_latest_metadata_delegates(self) -> None:
        metadata = Metadata.create("face")
        self.metadata_bus.latest.return_value = metadata

        result = self.service.latest_metadata("face")

        self.assertIs(result, metadata)
        self.metadata_bus.latest.assert_called_once_with("face")

    def test_statistics_composes_component_status(self) -> None:
        self.service._running = True

        self.frame_source.statistics.return_value = {
            "running": True,
            "fps": 15.0,
        }
        self.streamer.statistics.return_value = {
            "running": True,
            "clients": 2,
            "overlay": {
                "enabled": False,
                "source": None,
            },
        }
        self.streamer.overlay_status.return_value = {
            "enabled": True,
            "source": "face",
        }
        self.recording.is_recording.return_value = True
        self.recording.overlay_status.return_value = {
            "enabled": False,
            "source": None,
        }
        self.detection.names.return_value = [
            "color",
            "face",
        ]
        self.detection.is_enabled.side_effect = lambda name: name == "face"
        self.metadata_bus.all_latest.return_value = {
            "face": Metadata.create("face"),
        }

        stats = self.service.statistics()

        self.assertEqual(stats["running"], True)
        self.assertEqual(
            stats["camera"],
            {
                "running": True,
                "fps": 15.0,
            },
        )
        self.assertEqual(stats["streaming"]["clients"], 2)
        self.assertEqual(
            stats["streaming"]["overlay"],
            {
                "enabled": True,
                "source": "face",
            },
        )
        self.assertEqual(stats["recording"]["active"], True)
        self.assertEqual(
            stats["detection"],
            {
                "detectors": {
                    "color": False,
                    "face": True,
                },
                "metadata_sources": [
                    "face",
                ],
            },
        )
        self.assertEqual(
            stats["server"],
            {
                "host": "127.0.0.1",
                "port": 9000,
                "fps": 15,
            },
        )

    def test_close_delegates_to_stop(self) -> None:
        with patch.object(
            self.service,
            "stop",
        ) as stop:
            self.service.close()

        stop.assert_called_once_with()

    def test_context_manager_starts_and_stops_service(self) -> None:
        with (
            patch.object(
                self.service,
                "start",
            ) as start,
            patch.object(
                self.service,
                "stop",
            ) as stop,
            self.service as value,
        ):
            self.assertIs(value, self.service)

        start.assert_called_once_with()
        stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
