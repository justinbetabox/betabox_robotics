from __future__ import annotations

import threading
import time
from typing import Any, Self

from betabox_robotics.hardware import HardwareError
from betabox_robotics.vision.frame import Frame


class CameraError(HardwareError):
    """Raised when a camera operation fails."""


class CameraManager:
    """
    Single owner of the camera hardware.

    Picamera2 delivers frames through ``post_callback``. No other Vision
    component should open Picamera2 directly or use its synchronous capture
    methods.

    ``capture_frame()`` waits for the next callback-produced frame. It does
    not request a frame directly from Picamera2.
    """

    def __init__(
        self,
        resolution: tuple[int, int] = (640, 480),
        format: str = "BGR888",
    ) -> None:
        self.resolution = resolution
        self.format = format

        self._camera: Any | None = None
        self._running = False

        self._frame_ready = threading.Condition()
        self._latest_frame: Frame | None = None
        self._frame_sequence = 0
        self._callback_error: CameraError | None = None

        self._diagnostics_lock = threading.Lock()
        self._callback_frame_count = 0
        self._last_callback_completed: float | None = None

        self._frame_wait_in_progress = False
        self._last_frame_wait_duration: float | None = None
        self._max_frame_wait_duration = 0.0

    def start(self) -> None:
        """Open, configure, and start the camera."""

        with self._frame_ready:
            if self._running:
                return

        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise CameraError("Picamera2 is not installed or unavailable") from exc

        camera: Any | None = None

        try:
            camera = Picamera2()

            config = camera.create_video_configuration(
                main={
                    "size": self.resolution,
                    "format": self.format,
                }
            )

            camera.configure(config)
            camera.post_callback = self._on_frame

            with self._frame_ready:
                self._camera = camera
                self._latest_frame = None
                self._frame_sequence = 0
                self._callback_error = None
                self._running = True

            with self._diagnostics_lock:
                self._callback_frame_count = 0
                self._last_callback_completed = None
                self._frame_wait_in_progress = False
                self._last_frame_wait_duration = None
                self._max_frame_wait_duration = 0.0

            camera.start()

        except Exception as exc:
            with self._frame_ready:
                self._running = False
                self._camera = None
                self._frame_ready.notify_all()

            if camera is not None:
                try:
                    camera.post_callback = None
                except Exception:
                    pass

                try:
                    camera.close()
                except Exception:
                    pass

            raise CameraError(f"failed to start camera: {exc}") from exc

    def stop(self) -> None:
        """Stop and close the camera."""

        with self._frame_ready:
            self._running = False
            camera = self._camera
            self._camera = None
            self._frame_ready.notify_all()

        with self._diagnostics_lock:
            self._frame_wait_in_progress = False

        stop_error: Exception | None = None

        if camera is not None:
            try:
                camera.post_callback = None
            except Exception:
                pass

            try:
                camera.stop()
            except Exception as exc:
                stop_error = exc

            try:
                camera.close()
            except Exception as exc:
                if stop_error is None:
                    stop_error = exc

        with self._frame_ready:
            self._latest_frame = None
            self._frame_sequence = 0
            self._callback_error = None
            self._frame_ready.notify_all()

        if stop_error is not None:
            raise CameraError(f"failed to stop camera: {stop_error}") from stop_error

    def is_running(self) -> bool:
        """Return whether the camera is currently running."""

        with self._frame_ready:
            return self._running

    def capture_frame(self, *, timeout: float | None = None) -> Frame:
        """
        Wait for and return the next callback-produced frame.

        Args:
            timeout:
                Maximum number of seconds to wait. When omitted, wait until a
                frame arrives, the camera stops, or the callback reports an
                error.

        Raises:
            CameraError:
                If the camera is stopped, the callback fails, or the timeout
                expires.
        """

        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        started = time.monotonic()
        deadline = None if timeout is None else started + timeout

        with self._frame_ready:
            if not self._running:
                raise CameraError("camera is not running")

            expected_sequence = self._frame_sequence

        with self._diagnostics_lock:
            self._frame_wait_in_progress = True

        try:
            with self._frame_ready:
                while (
                    self._running
                    and self._callback_error is None
                    and self._frame_sequence <= expected_sequence
                ):
                    if deadline is None:
                        self._frame_ready.wait()
                        continue

                    remaining = deadline - time.monotonic()

                    if remaining <= 0:
                        raise CameraError("timed out waiting for camera frame")

                    self._frame_ready.wait(timeout=remaining)

                if self._callback_error is not None:
                    raise self._callback_error

                if not self._running:
                    raise CameraError("camera stopped while waiting for frame")

                if self._latest_frame is None:
                    raise CameraError("camera produced no frame")

                return self._latest_frame

        finally:
            duration = time.monotonic() - started

            with self._diagnostics_lock:
                self._frame_wait_in_progress = False
                self._last_frame_wait_duration = duration
                self._max_frame_wait_duration = max(
                    self._max_frame_wait_duration,
                    duration,
                )

    def latest_frame(self) -> Frame:
        """
        Return the most recently produced frame.

        If no frame has been produced yet, wait for the first frame.
        """

        with self._frame_ready:
            frame = self._latest_frame

        if frame is not None:
            return frame

        return self.capture_frame()

    def statistics(self) -> dict[str, Any]:
        """Return camera callback and frame-wait diagnostics."""

        now = time.monotonic()

        with self._frame_ready:
            running = self._running

        with self._diagnostics_lock:
            last_callback = self._last_callback_completed

            return {
                "running": running,
                "callback_frame_count": self._callback_frame_count,
                "frame_wait_in_progress": self._frame_wait_in_progress,
                "last_frame_wait_duration_seconds": (self._last_frame_wait_duration),
                "max_frame_wait_duration_seconds": (self._max_frame_wait_duration),
                "seconds_since_last_callback_frame": (
                    None if last_callback is None else now - last_callback
                ),
            }

    def _on_frame(self, request: Any) -> None:
        """
        Process a completed Picamera2 request.

        This callback is the only place where camera request data is converted
        into a Betabox ``Frame``.
        """

        with self._frame_ready:
            if not self._running:
                return

        try:
            image = request.make_array("main").copy()
            frame = Frame.create(image)
            completed = time.monotonic()

        except Exception as exc:
            error = CameraError(f"failed to process camera frame: {exc}")

            with self._frame_ready:
                if self._running:
                    self._callback_error = error
                    self._frame_ready.notify_all()

            return

        with self._frame_ready:
            if not self._running:
                return

            self._latest_frame = frame
            self._frame_sequence += 1
            self._frame_ready.notify_all()

        with self._diagnostics_lock:
            self._callback_frame_count += 1
            self._last_callback_completed = completed

    def configure(
        self,
        *,
        resolution: tuple[int, int] | None = None,
        format: str | None = None,
    ) -> None:
        """Update camera configuration while the camera is stopped."""

        with self._frame_ready:
            if self._running:
                raise CameraError("cannot configure camera while running")

        if resolution is not None:
            width, height = resolution

            if width <= 0 or height <= 0:
                raise ValueError("camera resolution must be positive")

            self.resolution = resolution

        if format is not None:
            if not format:
                raise ValueError("camera format cannot be empty")

            self.format = format

    def close(self) -> None:
        self.stop()

    def deinit(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        self.close()
