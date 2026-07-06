import threading
import time
from typing import Optional

from betabox_robotics.vision.camera import CameraError, CameraManager
from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame


class FrameSourceError(CameraError):
    """Raised when frame source operations fail."""


class FrameSource:
    """
    Continuously captures frames from the CameraManager and publishes
    them to registered consumers.
    """

    def __init__(
        self,
        camera: Optional[CameraManager] = None,
        *,
        fps: float = 20.0,
    ) -> None:
        if fps <= 0:
            raise FrameSourceError("fps must be greater than 0")

        self.camera = camera or CameraManager()
        self.fps = float(fps)

        self._latest_frame: Optional[Frame] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._consumer_lock = threading.Lock()
        self._consumers: list[FrameConsumer] = []
        self._last_error: Optional[Exception] = None

    def start(self) -> None:
        if self._running:
            return

        self.camera.start()
        self._running = True
        self._last_error = None

        self._thread = threading.Thread(
            target=self._capture_loop,
            name="BetaboxFrameSource",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        self.camera.stop()

        with self._lock:
            self._latest_frame = None

    def is_running(self) -> bool:
        return self._running

    def register_consumer(self, consumer: FrameConsumer) -> None:
        with self._consumer_lock:
            if consumer not in self._consumers:
                self._consumers.append(consumer)

    def unregister_consumer(self, consumer: FrameConsumer) -> None:
        with self._consumer_lock:
            if consumer in self._consumers:
                self._consumers.remove(consumer)

    def consumer_count(self) -> int:
        with self._consumer_lock:
            return len(self._consumers)

    def latest_frame(self) -> Frame:
        with self._lock:
            frame = self._latest_frame

        if frame is None:
            raise FrameSourceError("no frame available yet")

        return frame

    def last_error(self) -> Optional[Exception]:
        return self._last_error

    def _capture_loop(self) -> None:
        interval = 1.0 / self.fps

        while self._running:
            start_time = time.monotonic()

            try:
                frame = self.camera.capture_frame()

                with self._lock:
                    self._latest_frame = frame

                self._publish(frame)

            except Exception as exc:
                self._last_error = exc
                self._running = False
                break

            elapsed = time.monotonic() - start_time
            sleep_time = max(0.0, interval - elapsed)

            if sleep_time > 0:
                time.sleep(sleep_time)

    def _publish(self, frame: Frame) -> None:
        with self._consumer_lock:
            consumers = list(self._consumers)

        for consumer in consumers:
            try:
                consumer.on_frame(frame)
            except Exception as exc:
                self._last_error = exc

    def close(self) -> None:
        self.stop()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
