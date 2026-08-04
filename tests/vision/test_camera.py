import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.vision.camera import (
    CameraError,
    CameraManager,
    _validate_format,
    _validate_resolution,
    _validate_timeout,
)
from betabox_robotics.vision.frame import Frame


class CameraValidationTests(unittest.TestCase):
    def test_resolution_validation(self) -> None:
        self.assertEqual(
            _validate_resolution((640, 480)),
            (640, 480),
        )

        for value in (
            [640, 480],
            (640,),
            "640x480",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                _validate_resolution(value)

        for value in (
            (True, 480),
            (640, False),
            (640.0, 480),
            (640, 480.0),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "resolution must contain two integers",
                ),
            ):
                _validate_resolution(value)

        for value in (
            (0, 480),
            (640, 0),
            (-1, 480),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "camera resolution must be positive",
                ),
            ):
                _validate_resolution(value)

    def test_format_validation(self) -> None:
        self.assertEqual(
            _validate_format("  BGR888  "),
            "BGR888",
        )

        with self.assertRaisesRegex(
            TypeError,
            "format must be a string",
        ):
            _validate_format(123)

        with self.assertRaisesRegex(
            ValueError,
            "camera format cannot be empty",
        ):
            _validate_format(" ")

    def test_timeout_validation(self) -> None:
        self.assertEqual(
            _validate_timeout(1),
            1.0,
        )

        for value in (
            True,
            "1",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "timeout must be a number",
                ),
            ):
                _validate_timeout(value)

        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "timeout must be greater than zero",
                ),
            ):
                _validate_timeout(value)

        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "timeout must be finite",
                ),
            ):
                _validate_timeout(value)

    def test_constructor_validates_configuration(self) -> None:
        cases = (
            (
                {
                    "resolution": [640, 480],
                },
                TypeError,
            ),
            (
                {
                    "resolution": (0, 480),
                },
                ValueError,
            ),
            (
                {
                    "format": 1,
                },
                TypeError,
            ),
            (
                {
                    "format": " ",
                },
                ValueError,
            ),
        )

        for kwargs, exception_type in cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(exception_type),
            ):
                CameraManager(
                    **kwargs,  # type: ignore[arg-type]
                )

    def test_constructor_normalizes_format(self) -> None:
        camera = CameraManager(
            format="  BGR888  ",
        )

        self.assertEqual(
            camera.format,
            "BGR888",
        )

    def test_configure_validates_values(self) -> None:
        camera = CameraManager()

        cases = (
            (
                {
                    "resolution": [1280, 720],
                },
                TypeError,
            ),
            (
                {
                    "resolution": (0, 720),
                },
                ValueError,
            ),
            (
                {
                    "format": 1,
                },
                TypeError,
            ),
            (
                {
                    "format": " ",
                },
                ValueError,
            ),
        )

        for kwargs, exception_type in cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(exception_type),
            ):
                camera.configure(
                    **kwargs,  # type: ignore[arg-type]
                )

    def test_configure_rejects_running_camera(self) -> None:
        camera = CameraManager()

        with camera._frame_ready:
            camera._running = True

        with self.assertRaisesRegex(
            CameraError,
            "cannot configure camera while running",
        ):
            camera.configure(
                resolution=(1280, 720),
            )

    def test_capture_validates_timeout(self) -> None:
        camera = CameraManager()

        for timeout, exception_type, message in (
            (
                True,
                TypeError,
                "timeout must be a number",
            ),
            (
                float("inf"),
                ValueError,
                "timeout must be finite",
            ),
            (
                0,
                ValueError,
                "timeout must be greater than zero",
            ),
        ):
            with (
                self.subTest(timeout=timeout),
                self.assertRaisesRegex(
                    exception_type,
                    message,
                ),
            ):
                camera.capture_frame(
                    timeout=timeout,  # type: ignore[arg-type]
                )


class CameraLifecycleTests(unittest.TestCase):
    def test_defaults(self) -> None:
        camera = CameraManager()

        self.assertEqual(
            camera.resolution,
            (640, 480),
        )
        self.assertEqual(
            camera.format,
            "BGR888",
        )
        self.assertFalse(camera.is_running())

    def test_configure_when_stopped(self) -> None:
        camera = CameraManager()

        camera.configure(
            resolution=(1280, 720),
            format="  RGB888  ",
        )

        self.assertEqual(
            camera.resolution,
            (1280, 720),
        )
        self.assertEqual(
            camera.format,
            "RGB888",
        )

    @patch("picamera2.Picamera2")
    def test_start_initializes_camera(
        self,
        mock_picamera2,
    ) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}

        camera = CameraManager()
        camera.start()

        self.assertTrue(camera.is_running())
        mock_camera.configure.assert_called_once()
        mock_camera.start.assert_called_once_with()

    @patch("picamera2.Picamera2")
    def test_start_is_idempotent(
        self,
        mock_picamera2,
    ) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}

        camera = CameraManager()

        camera.start()
        camera.start()

        mock_picamera2.assert_called_once_with()
        mock_camera.start.assert_called_once_with()

    @patch("picamera2.Picamera2")
    def test_start_failure_closes_partial_camera(
        self,
        mock_picamera2,
    ) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}
        mock_camera.start.side_effect = RuntimeError("start failed")

        camera = CameraManager()

        with self.assertRaisesRegex(
            CameraError,
            "failed to start camera",
        ):
            camera.start()

        self.assertFalse(camera.is_running())
        self.assertIsNone(camera._camera)
        self.assertIsNone(mock_camera.post_callback)
        mock_camera.close.assert_called_once_with()

    @patch("picamera2.Picamera2")
    def test_stop_closes_camera(
        self,
        mock_picamera2,
    ) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}

        camera = CameraManager()

        camera.start()
        camera.stop()

        self.assertFalse(camera.is_running())
        mock_camera.stop.assert_called_once_with()
        mock_camera.close.assert_called_once_with()

    def test_stop_is_idempotent(self) -> None:
        camera = CameraManager()

        camera.stop()
        camera.stop()

        self.assertFalse(camera.is_running())

    @patch("picamera2.Picamera2")
    def test_stop_closes_camera_after_stop_failure(
        self,
        mock_picamera2,
    ) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}
        mock_camera.stop.side_effect = RuntimeError("stop failed")

        camera = CameraManager()
        camera.start()

        with self.assertRaisesRegex(
            CameraError,
            "failed to stop camera",
        ):
            camera.stop()

        mock_camera.close.assert_called_once_with()
        self.assertFalse(camera.is_running())
        self.assertIsNone(camera._camera)

    @patch("picamera2.Picamera2")
    def test_stop_continues_after_callback_detach_failure(
        self,
        mock_picamera2,
    ) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}

        camera = CameraManager()
        camera.start()

        type(mock_camera).post_callback = property(
            fget=lambda instance: None,
            fset=MagicMock(side_effect=RuntimeError("detach failed")),
        )

        with self.assertRaisesRegex(
            CameraError,
            "failed to detach camera callback",
        ):
            camera.stop()

        mock_camera.stop.assert_called_once_with()
        mock_camera.close.assert_called_once_with()
        self.assertFalse(camera.is_running())

    @patch("picamera2.Picamera2")
    def test_context_manager_starts_and_stops_camera(
        self,
        mock_picamera2,
    ) -> None:
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.create_video_configuration.return_value = {}

        camera = CameraManager()

        with camera as entered:
            self.assertIs(
                entered,
                camera,
            )
            self.assertTrue(camera.is_running())

        self.assertFalse(camera.is_running())
        mock_camera.start.assert_called_once_with()
        mock_camera.stop.assert_called_once_with()
        mock_camera.close.assert_called_once_with()


class CameraFrameTests(unittest.TestCase):
    def test_capture_requires_running_camera(self) -> None:
        camera = CameraManager()

        with self.assertRaisesRegex(
            CameraError,
            "camera is not running",
        ):
            camera.capture_frame()

    def test_latest_frame_waits_when_none(self) -> None:
        camera = CameraManager()
        expected = Frame.create(object())

        camera.capture_frame = MagicMock(
            return_value=expected,
        )

        self.assertIs(
            camera.latest_frame(),
            expected,
        )
        camera.capture_frame.assert_called_once_with()

    def test_latest_frame_returns_cached_frame(self) -> None:
        camera = CameraManager()
        frame = Frame.create(object())

        with camera._frame_ready:
            camera._latest_frame = frame

        self.assertIs(
            camera.latest_frame(),
            frame,
        )

    def test_on_frame_publishes_frame(self) -> None:
        camera = CameraManager()

        request = MagicMock()
        request.make_array.return_value.copy.return_value = object()

        with camera._frame_ready:
            camera._running = True

        camera._on_frame(request)

        with camera._frame_ready:
            self.assertIsNotNone(camera._latest_frame)
            self.assertEqual(
                camera._frame_sequence,
                1,
            )

    def test_callback_error_wakes_waiters(self) -> None:
        camera = CameraManager()

        with camera._frame_ready:
            camera._running = True

        request = MagicMock()
        request.make_array.side_effect = RuntimeError("boom")

        camera._on_frame(request)

        with self.assertRaisesRegex(
            CameraError,
            "failed to process camera frame: boom",
        ):
            camera.capture_frame()

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
        self.assertEqual(
            stats["callback_frame_count"],
            0,
        )
        self.assertFalse(stats["frame_wait_in_progress"])
        self.assertIsNone(stats["last_frame_wait_duration_seconds"])
        self.assertEqual(
            stats["max_frame_wait_duration_seconds"],
            0.0,
        )
        self.assertIsNone(stats["seconds_since_last_callback_frame"])


if __name__ == "__main__":
    unittest.main()
