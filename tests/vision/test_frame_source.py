import unittest
from unittest.mock import MagicMock

from betabox_robotics.vision.camera import CameraError, CameraManager
from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import (
    FrameSource,
    FrameSourceError,
)


class FrameSourceTests(unittest.TestCase):
    def test_default_configuration(self):
        source = FrameSource()

        self.assertEqual(source.fps, 20.0)
        self.assertFalse(source.is_running())
        self.assertEqual(source.consumer_count(), 0)

    def test_invalid_fps(self):
        with self.assertRaises(FrameSourceError):
            FrameSource(fps=0)

        with self.assertRaises(FrameSourceError):
            FrameSource(fps=-5)

    def test_register_consumer(self):
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)

        self.assertEqual(source.consumer_count(), 1)

    def test_duplicate_consumer_only_registered_once(self):
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)
        source.register_consumer(consumer)

        self.assertEqual(source.consumer_count(), 1)

    def test_unregister_consumer(self):
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)
        source.unregister_consumer(consumer)

        self.assertEqual(source.consumer_count(), 0)

    def test_latest_frame_before_capture_raises(self):
        source = FrameSource()

        with self.assertRaises(FrameSourceError):
            source.latest_frame()

    def test_latest_frame_returns_cached_frame(self):
        source = FrameSource()

        frame = Frame.create(object())

        with source._lock:
            source._latest_frame = frame

        self.assertIs(source.latest_frame(), frame)

    def test_publish_calls_consumer(self):
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)

        frame = Frame.create(object())

        source._publish(frame)

        stats = source.statistics()

        consumer_stats = stats["consumers"][type(consumer).__name__]

        self.assertEqual(consumer_stats["call_count"], 1)
        self.assertEqual(consumer_stats["error_count"], 0)
        self.assertIsNone(consumer_stats["last_error"])

        consumer.on_frame.assert_called_once_with(frame)

    def test_publish_continues_after_consumer_error(self):
        source = FrameSource()

        bad = MagicMock(spec=FrameConsumer)
        good = MagicMock(spec=FrameConsumer)

        bad.on_frame.side_effect = RuntimeError("boom")

        source.register_consumer(bad)
        source.register_consumer(good)

        frame = Frame.create(object())

        source._publish(frame)

        bad.on_frame.assert_called_once_with(frame)
        good.on_frame.assert_called_once_with(frame)

        self.assertIsInstance(source.last_error(), FrameSourceError)
        self.assertIn("failed: boom", str(source.last_error()))

        stats = source.statistics()
        consumer_stats = stats["consumers"][type(bad).__name__]

        self.assertEqual(consumer_stats["error_count"], 1)

    def test_statistics_initial_state(self):
        source = FrameSource()

        stats = source.statistics()

        self.assertEqual(
            set(stats),
            {
                "running",
                "thread_alive",
                "phase",
                "fps",
                "consumer_count",
                "has_frame",
                "frame_fresh",
                "frame_age_seconds",
                "freshness_threshold_seconds",
                "last_error",
                "camera_manager",
                "capture",
                "publish",
                "consumers",
            },
        )

        self.assertFalse(stats["running"])
        self.assertFalse(stats["thread_alive"])
        self.assertEqual(stats["phase"], "stopped")
        self.assertEqual(stats["fps"], 20.0)
        self.assertEqual(stats["consumer_count"], 0)
        self.assertFalse(stats["has_frame"])
        self.assertFalse(stats["frame_fresh"])
        self.assertIsNone(stats["frame_age_seconds"])
        self.assertEqual(stats["freshness_threshold_seconds"], 1.0)
        self.assertIsNone(stats["last_error"])
        self.assertEqual(stats["consumers"], {})

    def test_capture_loop_stops_after_camera_error(self):
        camera = MagicMock(spec=CameraManager)
        camera.capture_frame.side_effect = CameraError("boom")

        source = FrameSource(camera=camera)
        source._running = True

        source._capture_loop()

        camera.capture_frame.assert_called_once()

        self.assertFalse(source.is_running())
        self.assertIsInstance(source.last_error(), CameraError)

    def test_age_none(self):
        self.assertIsNone(FrameSource._age(10.0, None))

    def test_age(self):
        self.assertEqual(
            FrameSource._age(10.0, 8.5),
            1.5,
        )

    def test_consumer_statistics_created(self):
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)

        stats = source.statistics()

        self.assertIn(
            type(consumer).__name__,
            stats["consumers"],
        )

    def test_unregister_unknown_consumer(self):
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        # Should not raise
        source.unregister_consumer(consumer)

        self.assertEqual(source.consumer_count(), 0)
