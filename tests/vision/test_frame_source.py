import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.vision.camera import CameraError, CameraManager
from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import (
    FrameSource,
    FrameSourceError,
)


class GoodConsumer(FrameConsumer):
    def __init__(self) -> None:
        self.frames: list[Frame] = []

    def on_frame(
        self,
        frame: Frame,
    ) -> None:
        self.frames.append(frame)


class BadConsumer(FrameConsumer):
    def on_frame(
        self,
        frame: Frame,
    ) -> None:
        raise RuntimeError("boom")


class FrameSourceValidationTests(unittest.TestCase):
    def test_default_configuration(self) -> None:
        source = FrameSource()

        self.assertEqual(source.fps, 20.0)
        self.assertFalse(source.is_running())
        self.assertEqual(source.consumer_count(), 0)

    def test_invalid_fps(self) -> None:
        for value in (
            0,
            -5,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be greater than 0",
                ),
            ):
                FrameSource(fps=value)

    def test_fps_requires_finite_number(self) -> None:
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
                FrameSource(
                    fps=value,  # type: ignore[arg-type]
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
                    "fps must be finite",
                ),
            ):
                FrameSource(fps=value)


class FrameSourceConsumerTests(unittest.TestCase):
    def test_register_consumer(self) -> None:
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)

        self.assertEqual(source.consumer_count(), 1)

    def test_duplicate_consumer_only_registered_once(self) -> None:
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)
        source.register_consumer(consumer)

        self.assertEqual(source.consumer_count(), 1)

    def test_unregister_consumer(self) -> None:
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)
        source.unregister_consumer(consumer)

        self.assertEqual(source.consumer_count(), 0)

    def test_unregister_unknown_consumer(self) -> None:
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        # Should not raise
        source.unregister_consumer(consumer)

        self.assertEqual(source.consumer_count(), 0)

    def test_publish_calls_consumer(self) -> None:
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

    def test_publish_continues_after_consumer_error(self) -> None:
        source = FrameSource()

        bad = BadConsumer()
        good = GoodConsumer()

        source.register_consumer(bad)
        source.register_consumer(good)

        frame = Frame.create(object())

        source._publish(frame)

        self.assertEqual(
            good.frames,
            [frame],
        )

        self.assertIsInstance(source.last_error(), FrameSourceError)
        self.assertIn("failed: boom", str(source.last_error()))

        stats = source.statistics()
        consumer_stats = stats["consumers"][type(bad).__name__]

        self.assertEqual(consumer_stats["error_count"], 1)

    def test_consumer_statistics_created(self) -> None:
        source = FrameSource()

        consumer = MagicMock(spec=FrameConsumer)

        source.register_consumer(consumer)

        stats = source.statistics()

        self.assertIn(
            type(consumer).__name__,
            stats["consumers"],
        )


class FrameSourceLifecycleTests(unittest.TestCase):
    def test_start_starts_camera_and_worker(self) -> None:
        camera = MagicMock(spec=CameraManager)
        source = FrameSource(camera=camera)

        thread = MagicMock()

        with patch(
            "betabox_robotics.vision.frame_source.threading.Thread",
            return_value=thread,
        ):
            source.start()

        camera.start.assert_called_once_with()
        thread.start.assert_called_once_with()
        self.assertTrue(source.is_running())
        self.assertIs(source._thread, thread)

    def test_start_rolls_back_camera_when_thread_fails(self) -> None:
        camera = MagicMock(spec=CameraManager)
        source = FrameSource(camera=camera)

        thread = MagicMock()
        thread.start.side_effect = RuntimeError("thread failed")

        with (
            patch(
                "betabox_robotics.vision.frame_source.threading.Thread",
                return_value=thread,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "thread failed",
            ),
        ):
            source.start()

        camera.start.assert_called_once_with()
        camera.stop.assert_called_once_with()
        self.assertFalse(source.is_running())
        self.assertIsNone(source._thread)

    def test_stop_stops_camera_before_joining_thread(self) -> None:
        events: list[str] = []

        camera = MagicMock(spec=CameraManager)
        camera.stop.side_effect = lambda: events.append("camera.stop")

        thread = MagicMock()
        thread.join.side_effect = lambda timeout: events.append("thread.join")
        thread.is_alive.return_value = False

        source = FrameSource(camera=camera)
        source._running = True
        source._thread = thread

        source.stop()

        self.assertEqual(
            events,
            [
                "camera.stop",
                "thread.join",
            ],
        )
        thread.join.assert_called_once_with(
            timeout=2.0,
        )
        self.assertIsNone(source._thread)

    def test_stop_raises_when_thread_does_not_stop(self) -> None:
        camera = MagicMock(spec=CameraManager)
        thread = MagicMock()
        thread.is_alive.return_value = True

        source = FrameSource(camera=camera)
        source._running = True
        source._thread = thread

        with self.assertRaisesRegex(
            FrameSourceError,
            "frame source thread did not stop within 2 seconds",
        ):
            source.stop()

        camera.stop.assert_called_once_with()
        thread.join.assert_called_once_with(
            timeout=2.0,
        )

    def test_context_manager_starts_and_stops_source(self) -> None:
        camera = MagicMock(spec=CameraManager)
        source = FrameSource(camera=camera)

        thread = MagicMock()
        thread.is_alive.return_value = False

        with (
            patch(
                "betabox_robotics.vision.frame_source.threading.Thread",
                return_value=thread,
            ),
            source as entered,
        ):
            self.assertIs(
                entered,
                source,
            )
            self.assertTrue(source.is_running())

        camera.start.assert_called_once_with()
        camera.stop.assert_called_once_with()
        thread.start.assert_called_once_with()
        thread.join.assert_called_once_with(
            timeout=2.0,
        )


class FrameSourceFrameTests(unittest.TestCase):
    def test_latest_frame_before_capture_raises(self) -> None:
        source = FrameSource()

        with self.assertRaisesRegex(
            FrameSourceError,
            "no frame available",
        ):
            source.latest_frame()

    def test_latest_frame_returns_cached_frame(self) -> None:
        source = FrameSource()

        frame = Frame.create(object())

        with source._lock:
            source._latest_frame = frame

        self.assertIs(source.latest_frame(), frame)

    def test_capture_loop_stops_after_camera_error(self) -> None:
        camera = MagicMock(spec=CameraManager)
        camera.capture_frame.side_effect = CameraError("boom")

        source = FrameSource(camera=camera)
        source._running = True

        source._capture_loop()

        camera.capture_frame.assert_called_once()

        self.assertFalse(source.is_running())
        self.assertIsInstance(
            source.last_error(),
            FrameSourceError,
        )
        self.assertEqual(
            str(source.last_error()),
            "frame capture failed: boom",
        )


class FrameSourceStatisticsTests(unittest.TestCase):
    def test_statistics_initial_state(self) -> None:
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

    def test_age_none(self) -> None:
        self.assertIsNone(FrameSource._age(10.0, None))

    def test_age(self) -> None:
        self.assertEqual(
            FrameSource._age(10.0, 8.5),
            1.5,
        )
