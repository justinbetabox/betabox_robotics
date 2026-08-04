from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import (
    FrameSource,
    FrameSourceError,
)
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.recording import RecordingError
from betabox_robotics.vision.vision import Vision


class VisionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.frame_source = MagicMock(spec=FrameSource)
        self.frame_source.fps = 20.0

        self.metadata_bus = MetadataBus()

        self.overlay = MagicMock()
        self.detection = MagicMock()
        self.snapshot = MagicMock()
        self.recording = MagicMock()

        self.recording.is_recording.return_value = False
        self.detection.names.return_value = [
            "color",
            "face",
            "objects",
        ]
        self.detection.is_enabled.side_effect = lambda name: name == "color"

        self.patchers = (
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
        )

        self.mocks = [patcher.start() for patcher in self.patchers]

        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()

    def create_vision(self) -> Vision:
        return Vision(
            frame_source=self.frame_source,
            metadata_bus=self.metadata_bus,
        )


class VisionConstructionTests(VisionTestCase):
    def test_rejects_invalid_frame_source(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "frame_source must be a FrameSource",
        ):
            Vision(
                frame_source=object(),  # type: ignore[arg-type]
            )

    def test_rejects_invalid_metadata_bus(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "metadata_bus must be a MetadataBus",
        ):
            Vision(
                metadata_bus=object(),  # type: ignore[arg-type]
            )

    def test_uses_supplied_dependencies(self) -> None:
        vision = self.create_vision()

        self.assertIs(
            vision.frame_source,
            self.frame_source,
        )
        self.assertIs(
            vision.metadata,
            self.metadata_bus,
        )
        self.assertIs(
            vision.overlay,
            self.overlay,
        )
        self.assertIs(
            vision.detection,
            self.detection,
        )
        self.assertIs(
            vision.snapshot,
            self.snapshot,
        )
        self.assertIs(
            vision.recording,
            self.recording,
        )

    def test_constructs_components_with_shared_dependencies(
        self,
    ) -> None:
        self.create_vision()

        self.mocks[0].assert_called_once_with()
        self.mocks[1].assert_called_once_with(self.metadata_bus)
        self.mocks[2].assert_called_once_with(self.frame_source)
        self.mocks[3].assert_called_once_with(
            fps=20.0,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )

    def test_registers_recording_and_detection_consumers(
        self,
    ) -> None:
        self.create_vision()

        self.assertEqual(
            self.frame_source.register_consumer.call_args_list,
            [
                call(self.recording),
                call(self.detection),
            ],
        )

    def test_default_creates_vision(self) -> None:
        with (
            patch(
                "betabox_robotics.vision.vision.FrameSource",
                return_value=self.frame_source,
            ) as frame_source_type,
            patch(
                "betabox_robotics.vision.vision.MetadataBus",
                return_value=self.metadata_bus,
            ) as metadata_bus_type,
        ):
            vision = Vision.default(robot_config=object())

        self.assertIsInstance(
            vision,
            Vision,
        )
        frame_source_type.assert_called_once_with()
        metadata_bus_type.assert_called_once_with()


class VisionLifecycleTests(VisionTestCase):
    def test_start_delegates_to_frame_source(self) -> None:
        vision = self.create_vision()

        vision.start()

        self.frame_source.start.assert_called_once_with()

    def test_stop_stops_frame_source(self) -> None:
        vision = self.create_vision()

        vision.stop()

        self.recording.stop.assert_not_called()
        self.frame_source.stop.assert_called_once_with()

    def test_stop_finishes_active_recording(self) -> None:
        vision = self.create_vision()
        self.recording.is_recording.return_value = True

        vision.stop()

        self.recording.stop.assert_called_once_with()
        self.frame_source.stop.assert_called_once_with()

    def test_stop_preserves_recording_error(self) -> None:
        vision = self.create_vision()
        self.recording.is_recording.return_value = True

        failure = RecordingError("recording failed")
        self.recording.stop.side_effect = failure

        with self.assertRaisesRegex(
            RecordingError,
            "recording failed",
        ) as context:
            vision.stop()

        self.assertIs(
            context.exception,
            failure,
        )
        self.frame_source.stop.assert_called_once_with()

    def test_stop_raises_frame_source_error(self) -> None:
        vision = self.create_vision()

        failure = FrameSourceError("camera failed")
        self.frame_source.stop.side_effect = failure

        with self.assertRaisesRegex(
            FrameSourceError,
            "camera failed",
        ) as context:
            vision.stop()

        self.assertIs(
            context.exception,
            failure,
        )

    def test_stop_preserves_first_shutdown_error(
        self,
    ) -> None:
        vision = self.create_vision()
        self.recording.is_recording.return_value = True

        recording_failure = RecordingError("recording failed")
        frame_failure = FrameSourceError("camera failed")

        self.recording.stop.side_effect = recording_failure
        self.frame_source.stop.side_effect = frame_failure

        with self.assertRaisesRegex(
            RecordingError,
            "recording failed",
        ) as context:
            vision.stop()

        self.assertIs(
            context.exception,
            recording_failure,
        )
        self.frame_source.stop.assert_called_once_with()

    def test_close_delegates_to_stop(self) -> None:
        vision = self.create_vision()

        with patch.object(
            vision,
            "stop",
        ) as stop:
            vision.close()

        stop.assert_called_once_with()

    def test_deinit_delegates_to_close(self) -> None:
        vision = self.create_vision()

        with patch.object(
            vision,
            "close",
        ) as close:
            vision.deinit()

        close.assert_called_once_with()


class VisionDetectionTests(VisionTestCase):
    def test_enable_detection(self) -> None:
        vision = self.create_vision()

        vision.enable_detection("face")

        self.detection.enable.assert_called_once_with("face")

    def test_disable_detection(self) -> None:
        vision = self.create_vision()

        vision.disable_detection("face")

        self.detection.disable.assert_called_once_with("face")

    def test_enable_color_detection(self) -> None:
        vision = self.create_vision()

        custom_ranges = {
            "team_marker": (
                (
                    (10, 100, 100),
                    (20, 255, 255),
                ),
            ),
        }

        vision.enable_color_detection(
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

    def test_disable_color_detection(self) -> None:
        vision = self.create_vision()

        vision.disable_color_detection()

        self.detection.disable.assert_called_once_with("color")

    def test_detection_names(self) -> None:
        vision = self.create_vision()

        self.assertEqual(
            vision.detection_names(),
            [
                "color",
                "face",
                "objects",
            ],
        )

    def test_detection_status(self) -> None:
        vision = self.create_vision()

        self.assertEqual(
            vision.detection_status(),
            {
                "color": True,
                "face": False,
                "objects": False,
            },
        )

    def test_latest_metadata(self) -> None:
        vision = self.create_vision()

        metadata = Metadata.create(
            "color",
            timestamp=123.5,
        )
        self.metadata_bus.publish(metadata)

        self.assertIs(
            vision.latest_metadata("color"),
            metadata,
        )

    def test_latest_metadata_without_source(self) -> None:
        vision = self.create_vision()

        first = Metadata.create(
            "color",
            timestamp=1.0,
        )
        second = Metadata.create(
            "face",
            timestamp=2.0,
        )

        self.metadata_bus.publish(first)
        self.metadata_bus.publish(second)

        self.assertIs(
            vision.latest_metadata(),
            second,
        )


class VisionFrameTests(VisionTestCase):
    def test_is_running(self) -> None:
        vision = self.create_vision()
        self.frame_source.is_running.return_value = True

        self.assertTrue(vision.is_running())
        self.frame_source.is_running.assert_called_once_with()

    def test_latest_frame(self) -> None:
        vision = self.create_vision()

        frame = Frame.create(
            object(),
            timestamp=123.5,
        )
        self.frame_source.latest_frame.return_value = frame

        self.assertIs(
            vision.latest_frame(),
            frame,
        )
        self.frame_source.latest_frame.assert_called_once_with()

    def test_register_consumer(self) -> None:
        vision = self.create_vision()
        self.frame_source.register_consumer.reset_mock()

        consumer = MagicMock(spec=FrameConsumer)

        vision.register_consumer(consumer)

        self.frame_source.register_consumer.assert_called_once_with(consumer)

    def test_unregister_consumer(self) -> None:
        vision = self.create_vision()

        consumer = MagicMock(spec=FrameConsumer)

        vision.unregister_consumer(consumer)

        self.frame_source.unregister_consumer.assert_called_once_with(consumer)


class VisionContextManagerTests(VisionTestCase):
    def test_context_manager_starts_and_closes(
        self,
    ) -> None:
        vision = self.create_vision()

        with (
            patch.object(
                vision,
                "start",
            ) as start,
            patch.object(
                vision,
                "close",
            ) as close,
            vision as entered,
        ):
            self.assertIs(
                entered,
                vision,
            )

        start.assert_called_once_with()
        close.assert_called_once_with()

    def test_context_manager_closes_after_exception(
        self,
    ) -> None:
        vision = self.create_vision()

        with (
            patch.object(
                vision,
                "start",
            ),
            patch.object(
                vision,
                "close",
            ) as close,
            self.assertRaisesRegex(
                RuntimeError,
                "boom",
            ),
            vision,
        ):
            raise RuntimeError("boom")

        close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
