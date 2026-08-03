import threading
import time
from typing import Any

from betabox_robotics.vision.camera import CameraError, CameraManager
from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame


class FrameSourceError(CameraError):
    """Raised when frame source operations fail."""


class FrameSource:
    """
    Continuously captures frames from the CameraManager and publishes
    them to registered consumers.

    Capture, publication, and per-consumer timing information is retained
    so the Vision pipeline can identify where frame delivery has stalled.
    """

    def __init__(
        self,
        camera: CameraManager | None = None,
        *,
        fps: float = 20.0,
    ) -> None:
        if fps <= 0:
            raise FrameSourceError("fps must be greater than 0")

        self.camera = camera or CameraManager()
        self.fps = float(fps)

        self._latest_frame: Frame | None = None
        self._running = False
        self._thread: threading.Thread | None = None

        self._lock = threading.Lock()
        self._consumer_lock = threading.Lock()
        self._diagnostics_lock = threading.Lock()

        self._consumers: list[FrameConsumer] = []
        self._last_error: Exception | None = None

        # Capture-loop diagnostics use monotonic time because they measure
        # elapsed durations rather than wall-clock timestamps.
        self._phase = "stopped"
        self._capture_count = 0
        self._publish_count = 0

        self._last_cycle_started: float | None = None

        self._last_capture_started: float | None = None
        self._last_capture_completed: float | None = None
        self._last_capture_duration: float | None = None

        self._last_publish_started: float | None = None
        self._last_publish_completed: float | None = None
        self._last_publish_duration: float | None = None

        self._active_consumer: str | None = None
        self._active_consumer_started: float | None = None

        self._consumer_statistics: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        if self._running:
            return

        self.camera.start()
        self._running = True
        self._last_error = None

        with self._diagnostics_lock:
            self._phase = "starting"
            self._active_consumer = None
            self._active_consumer_started = None

        self._thread = threading.Thread(
            target=self._capture_loop,
            name="BetaboxFrameSource",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

        thread = self._thread

        if thread is not None:
            thread.join(timeout=2.0)

            if thread.is_alive():
                print(
                    "Vision warning: FrameSource thread did not stop within 2 seconds",
                    flush=True,
                )
            else:
                self._thread = None

        self.camera.stop()

        with self._lock:
            self._latest_frame = None

        with self._diagnostics_lock:
            if thread is None or not thread.is_alive():
                self._phase = "stopped"

            self._active_consumer = None
            self._active_consumer_started = None

    def is_running(self) -> bool:
        return self._running

    def register_consumer(self, consumer: FrameConsumer) -> None:
        with self._consumer_lock:
            if consumer not in self._consumers:
                self._consumers.append(consumer)

        consumer_name = type(consumer).__name__

        with self._diagnostics_lock:
            self._consumer_statistics.setdefault(
                consumer_name,
                self._new_consumer_statistics(),
            )

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

    def last_error(self) -> Exception | None:
        return self._last_error

    def statistics(self) -> dict[str, Any]:
        now = time.monotonic()

        with self._lock:
            has_frame = self._latest_frame is not None

        thread = self._thread
        thread_alive = thread is not None and thread.is_alive()

        with self._diagnostics_lock:
            phase = self._phase
            capture_count = self._capture_count
            publish_count = self._publish_count

            last_cycle_started = self._last_cycle_started

            last_capture_started = self._last_capture_started
            last_capture_completed = self._last_capture_completed
            last_capture_duration = self._last_capture_duration

            last_publish_started = self._last_publish_started
            last_publish_completed = self._last_publish_completed
            last_publish_duration = self._last_publish_duration

            active_consumer = self._active_consumer
            active_consumer_started = self._active_consumer_started

            consumer_statistics = {
                name: values.copy()
                for name, values in self._consumer_statistics.items()
            }

        frame_age = self._age(now, last_capture_completed)
        cycle_age = self._age(now, last_cycle_started)

        capture_in_progress = last_capture_started is not None and (
            last_capture_completed is None
            or last_capture_started > last_capture_completed
        )

        capture_in_progress_seconds = (
            self._age(now, last_capture_started) if capture_in_progress else None
        )

        publish_in_progress = last_publish_started is not None and (
            last_publish_completed is None
            or last_publish_started > last_publish_completed
        )

        publish_in_progress_seconds = (
            self._age(now, last_publish_started) if publish_in_progress else None
        )

        active_consumer_seconds = (
            self._age(now, active_consumer_started)
            if active_consumer is not None
            else None
        )

        # Five expected frame intervals, with a minimum tolerance of one
        # second, avoids marking brief scheduling delays as stale.
        freshness_threshold = max(1.0, 5.0 / self.fps)
        frame_fresh = (
            has_frame and frame_age is not None and frame_age <= freshness_threshold
        )

        for values in consumer_statistics.values():
            last_started = values.pop("_last_started", None)
            last_completed = values.pop("_last_completed", None)

            in_progress = last_started is not None and (
                last_completed is None or last_started > last_completed
            )

            values["in_progress"] = in_progress
            values["in_progress_seconds"] = (
                self._age(now, last_started) if in_progress else None
            )
            values["seconds_since_completion"] = self._age(
                now,
                last_completed,
            )

        return {
            "running": self._running,
            "thread_alive": thread_alive,
            "phase": phase,
            "fps": self.fps,
            "consumer_count": self.consumer_count(),
            "has_frame": has_frame,
            "frame_fresh": frame_fresh,
            "frame_age_seconds": frame_age,
            "freshness_threshold_seconds": freshness_threshold,
            "last_error": (str(self._last_error) if self._last_error else None),
            "camera_manager": self.camera.statistics(),
            "capture": {
                "count": capture_count,
                "cycle_age_seconds": cycle_age,
                "in_progress": capture_in_progress,
                "in_progress_seconds": capture_in_progress_seconds,
                "last_duration_seconds": last_capture_duration,
                "seconds_since_completion": self._age(
                    now,
                    last_capture_completed,
                ),
            },
            "publish": {
                "count": publish_count,
                "in_progress": publish_in_progress,
                "in_progress_seconds": publish_in_progress_seconds,
                "last_duration_seconds": last_publish_duration,
                "seconds_since_completion": self._age(
                    now,
                    last_publish_completed,
                ),
                "active_consumer": active_consumer,
                "active_consumer_seconds": active_consumer_seconds,
            },
            "consumers": consumer_statistics,
        }

    def _capture_loop(self) -> None:
        interval = 1.0 / self.fps

        with self._diagnostics_lock:
            self._phase = "running"

        while self._running:
            cycle_started = time.monotonic()

            with self._diagnostics_lock:
                self._last_cycle_started = cycle_started
                self._phase = "capturing"
                self._last_capture_started = cycle_started

            try:
                frame = self.camera.capture_frame()

                capture_completed = time.monotonic()

                with self._diagnostics_lock:
                    self._capture_count += 1
                    self._last_capture_completed = capture_completed
                    self._last_capture_duration = capture_completed - cycle_started

                with self._lock:
                    self._latest_frame = frame

                publish_started = time.monotonic()

                with self._diagnostics_lock:
                    self._phase = "publishing"
                    self._last_publish_started = publish_started

                self._publish(frame)

                publish_completed = time.monotonic()

                with self._diagnostics_lock:
                    self._publish_count += 1
                    self._last_publish_completed = publish_completed
                    self._last_publish_duration = publish_completed - publish_started
                    self._phase = "sleeping"

            except Exception as exc:
                self._last_error = exc

                with self._diagnostics_lock:
                    self._phase = "failed"
                    self._active_consumer = None
                    self._active_consumer_started = None

                self._running = False

                print(
                    f"Vision frame source error: {exc}",
                    flush=True,
                )
                break

            elapsed = time.monotonic() - cycle_started
            sleep_time = max(0.0, interval - elapsed)

            if sleep_time > 0:
                time.sleep(sleep_time)

        with self._diagnostics_lock:
            if self._phase != "failed":
                self._phase = "stopped"

    def _publish(
        self,
        frame: Frame,
    ) -> None:
        with self._consumer_lock:
            consumers = list(self._consumers)

        for consumer in consumers:
            consumer_name = type(consumer).__name__
            started = time.monotonic()

            with self._diagnostics_lock:
                statistics = self._consumer_statistics.setdefault(
                    consumer_name,
                    self._new_consumer_statistics(),
                )

                statistics["call_count"] += 1
                statistics["_last_started"] = started
                statistics["last_error"] = None

                self._active_consumer = consumer_name
                self._active_consumer_started = started

            try:
                consumer.on_frame(frame)

            except Exception as exc:
                wrapped = FrameSourceError(f"{consumer_name} failed: {exc}")

                self._last_error = wrapped

                with self._diagnostics_lock:
                    statistics = self._consumer_statistics[consumer_name]
                    statistics["error_count"] += 1
                    statistics["last_error"] = str(wrapped)

                print(
                    f"Vision consumer error: {wrapped}",
                    flush=True,
                )

            finally:
                completed = time.monotonic()
                elapsed = completed - started

                with self._diagnostics_lock:
                    statistics = self._consumer_statistics[consumer_name]

                    statistics["_last_completed"] = completed
                    statistics["last_duration_seconds"] = elapsed
                    statistics["max_duration_seconds"] = max(
                        statistics["max_duration_seconds"],
                        elapsed,
                    )

                    self._active_consumer = None
                    self._active_consumer_started = None

                if elapsed >= 0.05:
                    print(
                        "Vision consumer timing: "
                        f"{consumer_name} took "
                        f"{elapsed:.3f} seconds",
                        flush=True,
                    )

    @staticmethod
    def _new_consumer_statistics() -> dict[str, Any]:
        return {
            "call_count": 0,
            "error_count": 0,
            "last_duration_seconds": None,
            "max_duration_seconds": 0.0,
            "last_error": None,
            "_last_started": None,
            "_last_completed": None,
        }

    @staticmethod
    def _age(
        now: float,
        timestamp: float | None,
    ) -> float | None:
        if timestamp is None:
            return None

        return max(0.0, now - timestamp)

    def close(self) -> None:
        self.stop()

    def deinit(self) -> None:
        self.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
