from typing import Optional

from betabox_robotics.hardware import HardwareError
from betabox_robotics.vision.frame import Frame


class CameraError(HardwareError):
    """Raised when a camera operation fails."""


class CameraManager:
    """
    Single owner of the camera hardware.

    No other Vision component should open Picamera2 directly.
    """

    def __init__(self, resolution=(640, 480), format: str = "BGR888") -> None:
        self.resolution = resolution
        self.format = format
        self._camera = None
        self._running = False
        self._latest_frame: Optional[Frame] = None

    def start(self) -> None:
        if self._running:
            return

        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise CameraError("Picamera2 is not installed or unavailable") from exc

        try:
            self._camera = Picamera2()
            config = self._camera.create_video_configuration(
                main={
                    "size": self.resolution,
                    "format": self.format,
                }
            )
            self._camera.configure(config)
            self._camera.start()
            self._running = True
        except Exception as exc:
            self._camera = None
            self._running = False
            raise CameraError(f"failed to start camera: {exc}") from exc

    def stop(self) -> None:
        if self._camera is not None:
            try:
                self._camera.stop()
                self._camera.close()
            finally:
                self._camera = None
                self._running = False
                self._latest_frame = None

    def is_running(self) -> bool:
        return self._running

    def capture_frame(self) -> Frame:
        if not self._running or self._camera is None:
            raise CameraError("camera is not running")

        try:
            image = self._camera.capture_array()
        except Exception as exc:
            raise CameraError(f"failed to capture frame: {exc}") from exc

        frame = Frame.create(image)
        self._latest_frame = frame
        return frame

    def latest_frame(self) -> Frame:
        if self._latest_frame is None:
            return self.capture_frame()

        return self._latest_frame

    def configure(self, *, resolution=None, format: Optional[str] = None) -> None:
        if self._running:
            raise CameraError("cannot configure camera while running")

        if resolution is not None:
            self.resolution = resolution

        if format is not None:
            self.format = format

    def close(self) -> None:
        self.stop()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
