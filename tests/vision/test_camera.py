import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.vision.camera import CameraError, CameraManager
from betabox_robotics.vision.frame import Frame


class CameraManagerTests(unittest.TestCase):
    def test_defaults(self) -> None:
        camera = CameraManager()

        self.assertEqual(camera.resolution, (640, 480))
        self.assertEqual(camera.format, "BGR888")
        self.assertFalse(camera.is_running())

    def test_configure_when_stopped(self) -> None:
        camera = CameraManager()

        camera.configure(
            resolution=(1280, 720),
            format="RGB888",
        )

        self.assertEqual(camera.resolution, (1280, 720))
        self.assertEqual(camera.format, "RGB888")

    def test_capture_requires_running_camera(self) -> None:
        camera = CameraManager()

        with self.assertRaises(CameraError):
            camera.capture_frame()

    def test_latest_frame_waits_when_none(self) -> None:
        camera = CameraManager()

        expected = Frame.create(object())

        camera.capture_frame = MagicMock(return_value=expected)

        self.assertIs(camera.latest_frame(), expected)
        camera.capture_frame.assert_called_once()

    def test_latest_frame_returns_cached_frame(self) -> None:
        camera = CameraManager()

        frame = Frame.create(object())

        with camera._frame_ready:
            camera._latest_frame = frame

        self.assertIs(camera.latest_frame(), frame)

    @patch("picamera2.Picamera2")
    def test_start_initializes_camera(self, mock_picamera2) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}

        camera = CameraManager()

        camera.start()

        self.assertTrue(camera.is_running())
        mock_camera.configure.assert_called_once()
        mock_camera.start.assert_called_once()

    @patch("picamera2.Picamera2")
    def test_stop_closes_camera(self, mock_picamera2) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}

        camera = CameraManager()

        camera.start()
        camera.stop()

        self.assertFalse(camera.is_running())
        mock_camera.stop.assert_called_once()
        mock_camera.close.assert_called_once()

    def test_on_frame_publishes_frame(self) -> None:
        camera = CameraManager()

        request = MagicMock()
        request.make_array.return_value.copy.return_value = object()

        with camera._frame_ready:
            camera._running = True

        camera._on_frame(request)

        with camera._frame_ready:
            self.assertIsNotNone(camera._latest_frame)
            self.assertEqual(camera._frame_sequence, 1)

    def test_statistics_initial_state(self) -> None:
        camera = CameraManager()

        stats = camera.statistics()

        self.assertEqual(
            set(stats),
            {
                "running",
                "callback_frame_count",
                "frame_wait_in_progress",
                "last_frame_wait_duration_seconds",
                "max_frame_wait_duration_seconds",
                "seconds_since_last_callback_frame",
            },
        )

        self.assertFalse(stats["running"])
        self.assertEqual(stats["callback_frame_count"], 0)
        self.assertFalse(stats["frame_wait_in_progress"])
        self.assertIsNone(stats["last_frame_wait_duration_seconds"])
        self.assertEqual(stats["max_frame_wait_duration_seconds"], 0.0)
        self.assertIsNone(stats["seconds_since_last_callback_frame"])

    def test_callback_error_wakes_waiters(self) -> None:
        camera = CameraManager()

        with camera._frame_ready:
            camera._running = True

        request = MagicMock()
        request.make_array.side_effect = RuntimeError("boom")

        camera._on_frame(request)

        with self.assertRaises(CameraError):
            camera.capture_frame()
