import math
import threading
import time
from typing import Self, TypedDict

from betabox_robotics.vision.camera import (
    CameraError,
    CameraManager,
    CameraStatistics,
)
from betabox_robotics.vision.consumer import FrameConsumer, FrameConsumerError
from betabox_robotics.vision.frame import Frame


def _validate_fps(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("fps must be a number")

    fps = float(value)

    if not math.isfinite(fps):
        raise ValueError("fps must be finite")

    if fps <= 0:
        raise ValueError("fps must be greater than 0")

    return fps


class ConsumerStatistics(TypedDict):
    call_count: int
    error_count: int
    last_duration_seconds: float | None
    max_duration_seconds: float
    last_error: str | None
    _last_started: float | None
    _last_completed: float | None


class ConsumerDiagnostics(TypedDict):
    call_count: int
    error_count: int
    last_duration_seconds: float | None
    max_duration_seconds: float
    last_error: str | None
    in_progress: bool
    in_progress_seconds: float | None
    seconds_since_completion: float | None


class CaptureStatistics(TypedDict):
    count: int
    cycle_age_seconds: float | None
    in_progress: bool
    in_progress_seconds: float | None
    last_duration_seconds: float | None
    seconds_since_completion: float | None


class PublishStatistics(TypedDict):
    count: int
    in_progress: bool
    in_progress_seconds: float | None
    last_duration_seconds: float | None
    seconds_since_completion: float | None
    active_consumer: str | None
    active_consumer_seconds: float | None


class FrameSourceStatistics(TypedDict):
    running: bool
    thread_alive: bool
    phase: str
    fps: float
    consumer_count: int
    has_frame: bool
    frame_fresh: bool
    frame_age_seconds: float | None
    freshness_threshold_seconds: float
    last_error: str | None
    camera_manager: CameraStatistics
    capture: CaptureStatistics
    publish: PublishStatistics
    consumers: dict[str, ConsumerDiagnostics]


class FrameSourceError(CameraError):
    """Raised when frame source operations fail."""


class FrameSource:
    """
    Continuously captures frames from the CameraManager and publishes
    them to registered consumers.

    Capture, publication, and per-consumer timing information is retained
    so the Vision pipeline can identify where frame delivery has stalled.
    """

    camera: CameraManager
    fps: float

    _latest_frame: Frame | None
    _running: bool
    _thread: threading.Thread | None

    _lock: threading.Lock
    _consumer_lock: threading.Lock
    _diagnostics_lock: threading.Lock

    _consumers: list[FrameConsumer]
    _last_error: FrameSourceError | None

    _phase: str
    _capture_count: int
    _publish_count: int

    _last_cycle_started: float | None

    _last_capture_started: float | None
    _last_capture_completed: float | None
    _last_capture_duration: float | None

    _last_publish_started: float | None
    _last_publish_completed: float | None
    _last_publish_duration: float | None

    _active_consumer: str | None
    _active_consumer_started: float | None

    _consumer_statistics: dict[str, ConsumerStatistics]

    def __init__(
        self,
        camera: CameraManager | None = None,
        *,
        fps: float = 20.0,
    ) -> None:
        fps_value = _validate_fps(fps)

        self.camera = (
            camera
            if camera is not None
            else CameraManager(
                fps=fps_value,
            )
        )

        self.fps = fps_value

        self._latest_frame = None
        self._running = False
        self._thread = None

        self._lock = threading.Lock()
        self._consumer_lock = threading.Lock()
        self._diagnostics_lock = threading.Lock()

        self._consumers = []
        self._last_error = None

        # Capture-loop diagnostics use monotonic time because they measure
        # elapsed durations rather than wall-clock timestamps.
        self._phase = "stopped"
        self._capture_count = 0
        self._publish_count = 0

        self._last_cycle_started = None

        self._last_capture_started = None
        self._last_capture_completed = None
        self._last_capture_duration = None

        self._last_publish_started = None
        self._last_publish_completed = None
        self._last_publish_duration = None

        self._active_consumer = None
        self._active_consumer_started = None

        self._consumer_statistics = {}

    def start(self) -> None:
        if self._running:
            return

        thread = threading.Thread(
            target=self._capture_loop,
            name="BetaboxFrameSource",
            daemon=True,
        )

        try:
            self.camera.start()

            self._running = True
            self._last_error = None

            with self._diagnostics_lock:
                self._phase = "starting"
                self._active_consumer = None
                self._active_consumer_started = None

            thread.start()

        except RuntimeError:
            self._running = False

            try:
                self.camera.stop()
            except CameraError:
                pass

            raise

        self._thread = thread

    def stop(self) -> None:
        self._running = False

        thread = self._thread
        shutdown_error: CameraError | None = None

        try:
            self.camera.stop()
        except CameraError as exc:
            shutdown_error = exc

        if thread is not None:
            thread.join(timeout=2.0)

            if thread.is_alive():
                warning = FrameSourceError(
                    "frame source thread did not stop within 2 seconds"
                )

                if shutdown_error is None:
                    shutdown_error = warning
            else:
                self._thread = None

        with self._lock:
            self._latest_frame = None

        with self._diagnostics_lock:
            if thread is None or not thread.is_alive():
                self._phase = "stopped"

            self._active_consumer = None
            self._active_consumer_started = None

        if shutdown_error is not None:
            raise shutdown_error

    def is_running(self) -> bool:
        return self._running

    def register_consumer(self, consumer: FrameConsumer) -> None:
        with self._consumer_lock:
            if consumer not in self._consumers:
                self._consumers.append(consumer)

        consumer_name = type(consumer).__name__

        with self._diagnostics_lock:
            _ = self._consumer_statistics.setdefault(
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

    def last_error(self) -> FrameSourceError | None:
        return self._last_error

    def statistics(self) -> FrameSourceStatistics:
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

            consumer_statistics: dict[str, ConsumerDiagnostics] = {}

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

        for name, values in self._consumer_statistics.items():
            last_started = values["_last_started"]
            last_completed = values["_last_completed"]

            in_progress = last_started is not None and (
                last_completed is None or last_started > last_completed
            )

            consumer_statistics[name] = ConsumerDiagnostics(
                call_count=values["call_count"],
                error_count=values["error_count"],
                last_duration_seconds=values["last_duration_seconds"],
                max_duration_seconds=values["max_duration_seconds"],
                last_error=values["last_error"],
                in_progress=in_progress,
                in_progress_seconds=(
                    self._age(now, last_started) if in_progress else None
                ),
                seconds_since_completion=self._age(
                    now,
                    last_completed,
                ),
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

            except CameraError as exc:
                if (
                    not self._running
                    and "camera stopped while waiting for frame" in str(exc)
                ):
                    break

                failure = FrameSourceError(f"frame capture failed: {exc}")

                self._last_error = failure

                with self._diagnostics_lock:
                    self._phase = "failed"
                    self._active_consumer = None
                    self._active_consumer_started = None

                self._running = False

                print(
                    f"Vision frame source error: {failure}",
                    flush=True,
                )

                break

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

            except FrameConsumerError as exc:
                with self._diagnostics_lock:
                    statistics = self._consumer_statistics[consumer_name]

                    statistics["error_count"] += 1
                    statistics["last_error"] = str(exc)

                continue

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
                        f"Vision consumer timing: {consumer_name} took {elapsed:.3f} seconds",
                        flush=True,
                    )

    @staticmethod
    def _new_consumer_statistics() -> ConsumerStatistics:
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

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()
