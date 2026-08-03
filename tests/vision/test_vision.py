import unittest
from unittest.mock import MagicMock, call, patch

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.vision import Vision


class FalsyFrameSource:
    fps = 12.0

    def __init__(self) -> None:
        self.consumers = []

    def __bool__(self) -> bool:
        return False

    def register_consumer(self, consumer) -> None:
        self.consumers.append(consumer)


class FalsyMetadataBus:
    def __bool__(self) -> bool:
        return False


class VisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame_source = MagicMock()
        self.frame_source.fps = 15.0

        self.metadata_bus = MagicMock()
        self.overlay = MagicMock()
        self.detection = MagicMock()
        self.snapshot = MagicMock()
        self.recording = MagicMock()

        patchers = [
            patch(
                "betabox_robotics.vision.vision.FrameSource",
                return_value=self.frame_source,
            ),
            patch(
                "betabox_robotics.vision.vision.MetadataBus",
                return_value=self.metadata_bus,
            ),
            patch(
                "betabox_robotics.vision.vision.OverlayRenderer",
                return_value=self.overlay,
            ),
            patch(
                "betabox_robotics.vision.vision.DetectionManager",
                return_value=self.detection,
            ),
            patch(
                "betabox_robotics.vision.vision.SnapshotService",
                return_value=self.snapshot,
            ),
            patch(
                "betabox_robotics.vision.vision.RecordingService",
                return_value=self.recording,
            ),
        ]

        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.vision = Vision()

    def test_constructs_default_components(self) -> None:
        from betabox_robotics.vision import vision as vision_module

        vision_module.FrameSource.assert_called_once_with()
        vision_module.MetadataBus.assert_called_once_with()
        vision_module.OverlayRenderer.assert_called_once_with()

        vision_module.DetectionManager.assert_called_once_with(self.metadata_bus)
        vision_module.SnapshotService.assert_called_once_with(self.frame_source)
        vision_module.RecordingService.assert_called_once_with(
            fps=15.0,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )

        self.assertIs(
            self.vision.frame_source,
            self.frame_source,
        )
        self.assertIs(
            self.vision.metadata,
            self.metadata_bus,
        )
        self.assertIs(
            self.vision.overlay,
            self.overlay,
        )
        self.assertIs(
            self.vision.detection,
            self.detection,
        )
        self.assertIs(
            self.vision.snapshot,
            self.snapshot,
        )
        self.assertIs(
            self.vision.recording,
            self.recording,
        )

    def test_registers_recording_and_detection_consumers(self) -> None:
        self.assertEqual(
            self.frame_source.register_consumer.call_args_list,
            [
                call(self.recording),
                call(self.detection),
            ],
        )

    def test_uses_injected_dependencies(self) -> None:
        injected_source = MagicMock()
        injected_source.fps = 10.0
        injected_bus = MagicMock()

        with (
            patch("betabox_robotics.vision.vision.FrameSource") as frame_source_class,
            patch("betabox_robotics.vision.vision.MetadataBus") as metadata_bus_class,
        ):
            vision = Vision(
                frame_source=injected_source,
                metadata_bus=injected_bus,
            )

        frame_source_class.assert_not_called()
        metadata_bus_class.assert_not_called()

        self.assertIs(
            vision.frame_source,
            injected_source,
        )
        self.assertIs(
            vision.metadata,
            injected_bus,
        )

    def test_preserves_falsy_injected_dependencies(self) -> None:
        frame_source = FalsyFrameSource()
        metadata_bus = FalsyMetadataBus()

        vision = Vision(
            frame_source=frame_source,
            metadata_bus=metadata_bus,
        )

        self.assertIs(
            vision.frame_source,
            frame_source,
        )
        self.assertIs(
            vision.metadata,
            metadata_bus,
        )
        self.assertEqual(
            frame_source.consumers,
            [
                vision.recording,
                vision.detection,
            ],
        )

    def test_default_returns_vision_instance(self) -> None:
        vision = Vision.default()

        self.assertIsInstance(vision, Vision)

    def test_default_ignores_robot_config(self) -> None:
        config = object()

        vision = Vision.default(config)

        self.assertIsInstance(vision, Vision)

    def test_start_delegates_to_frame_source(self) -> None:
        self.vision.start()

        self.frame_source.start.assert_called_once_with()

    def test_stop_stops_frame_source_when_not_recording(self) -> None:
        self.recording.is_recording.return_value = False

        self.vision.stop()

        self.recording.stop.assert_not_called()
        self.frame_source.stop.assert_called_once_with()

    def test_stop_stops_active_recording_first(self) -> None:
        self.recording.is_recording.return_value = True

        self.vision.stop()

        self.recording.stop.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()

    def test_stop_still_stops_frame_source_when_recording_fails(
        self,
    ) -> None:
        self.recording.is_recording.return_value = True
        self.recording.stop.side_effect = RuntimeError("recording failed")

        with self.assertRaisesRegex(
            RuntimeError,
            "recording failed",
        ):
            self.vision.stop()

        self.recording.stop.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()

    def test_is_running_delegates(self) -> None:
        self.frame_source.is_running.return_value = True

        self.assertTrue(self.vision.is_running())

        self.frame_source.is_running.assert_called_once_with()

    def test_latest_frame_delegates(self) -> None:
        frame = Frame.create(object())
        self.frame_source.latest_frame.return_value = frame

        result = self.vision.latest_frame()

        self.assertIs(result, frame)
        self.frame_source.latest_frame.assert_called_once_with()

    def test_register_consumer_delegates(self) -> None:
        consumer = MagicMock()

        self.vision.register_consumer(consumer)

        self.frame_source.register_consumer.assert_called_with(consumer)

    def test_unregister_consumer_delegates(self) -> None:
        consumer = MagicMock()

        self.vision.unregister_consumer(consumer)

        self.frame_source.unregister_consumer.assert_called_once_with(consumer)

    def test_close_delegates_to_stop(self) -> None:
        with patch.object(
            self.vision,
            "stop",
        ) as stop:
            self.vision.close()

        stop.assert_called_once_with()

    def test_deinit_delegates_to_close(self) -> None:
        with patch.object(
            self.vision,
            "close",
        ) as close:
            self.vision.deinit()

        close.assert_called_once_with()

    def test_context_manager_starts_and_closes(self) -> None:
        with (
            patch.object(
                self.vision,
                "start",
            ) as start,
            patch.object(
                self.vision,
                "close",
            ) as close,
            self.vision as value,
        ):
            self.assertIs(
                value,
                self.vision,
            )

        start.assert_called_once_with()
        close.assert_called_once_with()

    def test_context_manager_closes_after_exception(self) -> None:
        with (
            patch.object(
                self.vision,
                "start",
            ),
            patch.object(
                self.vision,
                "close",
            ) as close,
            self.assertRaisesRegex(
                RuntimeError,
                "boom",
            ),
            self.vision,
        ):
            raise RuntimeError("boom")

        close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
