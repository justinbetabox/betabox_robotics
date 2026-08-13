import math
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from time import strftime
from typing import BinaryIO, Literal, cast

import cv2
from typing_extensions import override

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import (
    Frame,
    ImageArray,
)
from betabox_robotics.vision.frame_source import FrameSourceError
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import (
    OverlayError,
    OverlayRenderer,
)

RecordingFormat = Literal["mp4"]


def _validate_directory(
    value: object,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError("directory must be a string or Path")

    return Path(value).expanduser()


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


def _validate_filename(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("filename must be a string")

    filename = value.strip()

    if not filename:
        raise ValueError("filename cannot be empty")

    if Path(filename).name != filename:
        raise ValueError("filename must not contain a directory")

    return filename


def _validate_filename_prefix(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("filename_prefix must be a string")

    prefix = value.strip()

    if not prefix:
        raise ValueError("filename_prefix cannot be empty")

    if Path(prefix).name != prefix:
        raise ValueError("filename_prefix must not contain a directory")

    return prefix


@dataclass(frozen=True, slots=True)
class Recording:
    path: Path
    start_timestamp: float
    end_timestamp: float
    frame_count: int
    fps: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_timestamp - self.start_timestamp)


@dataclass(frozen=True, slots=True)
class RecordingData:
    data: bytes
    format: RecordingFormat
    start_timestamp: float
    end_timestamp: float
    frame_count: int
    fps: float


class RecordingError(FrameSourceError):
    """Raised when recording operations fail."""


class RecordingService(FrameConsumer):
    """
    Records frames from the Vision frame pipeline.

    RecordingService does not own or open the camera. It is registered
    as a FrameConsumer with FrameSource while recording.
    """

    directory: Path
    fps: float
    filename_prefix: str
    metadata_bus: MetadataBus | None
    overlay: OverlayRenderer
    overlay_enabled: bool
    overlay_source: str | None

    _process: subprocess.Popen[bytes] | None
    _path: Path | None
    _last_error: RecordingError | None
    _start_timestamp: float | None
    _end_timestamp: float | None
    _frame_count: int
    _recording: bool
    _size: tuple[int, int] | None

    _lock: threading.Lock
    _frame_condition: threading.Condition
    _pending_frame: Frame | None
    _worker: threading.Thread | None

    def __init__(
        self,
        *,
        directory: str | Path | None = None,
        fps: float = 20.0,
        filename_prefix: str = "recording",
        metadata_bus: MetadataBus | None = None,
        overlay: OverlayRenderer | None = None,
    ) -> None:
        self.directory = (
            Path("/tmp/betabox-video")
            if directory is None
            else _validate_directory(directory)
        )
        self.fps = _validate_fps(fps)
        self.filename_prefix = _validate_filename_prefix(filename_prefix)
        self.metadata_bus = metadata_bus
        self.overlay = overlay if overlay is not None else OverlayRenderer()
        self.overlay_enabled = False
        self.overlay_source = None

        self._process = None
        self._path = None
        self._last_error = None
        self._start_timestamp = None
        self._end_timestamp = None
        self._frame_count = 0
        self._recording = False
        self._size = None

        self._lock = threading.Lock()
        self._frame_condition = threading.Condition(self._lock)
        self._pending_frame = None
        self._worker = None

    def start(
        self,
        *,
        filename: str | None = None,
    ) -> Path:
        with self._frame_condition:
            if self._recording:
                raise RecordingError("recording is already running")

            if shutil.which("ffmpeg") is None:
                raise RecordingError("ffmpeg is not installed")

            try:
                self.directory.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                with tempfile.NamedTemporaryFile(
                    dir=self.directory,
                    prefix=".betabox-recording-test-",
                ):
                    pass

            except OSError as exc:
                raise RecordingError(
                    f"recording directory is not writable: {self.directory}: {exc}"
                ) from exc

            filename_value = (
                f"{self.filename_prefix}_{strftime('%Y%m%d_%H%M%S')}.mp4"
                if filename is None
                else _validate_filename(filename)
            )

            path = (self.directory / filename_value).with_suffix(".mp4")

            if path.suffix.lower() != ".mp4":
                path = path.with_suffix(".mp4")

            self._path = path
            self._process = None
            self._last_error = None
            self._start_timestamp = None
            self._end_timestamp = None
            self._frame_count = 0
            self._size = None
            self._pending_frame = None
            self._recording = True

            worker = threading.Thread(
                target=self._recording_loop,
                name="BetaboxRecording",
                daemon=True,
            )

            self._worker = worker

            try:
                worker.start()
            except RuntimeError:
                self._worker = None
                self._recording = False
                self._path = None
                raise

            return path

    def stop(self) -> Recording:
        with self._frame_condition:
            worker = self._worker

            if not self._recording and worker is None:
                if self._last_error is not None:
                    raise RecordingError(
                        f"recording failed: {self._last_error}"
                    ) from self._last_error

                raise RecordingError("recording is not running")

            self._recording = False
            self._frame_condition.notify_all()

        if worker is not None:
            worker.join(timeout=5.0)

            if worker.is_alive():
                self._abort_encoder()
                worker.join(timeout=5.0)

            if worker.is_alive():
                failure = RecordingError(
                    "recording worker did not stop within 10 seconds"
                )

                with self._lock:
                    self._last_error = failure

                raise failure

        with self._lock:
            self._worker = None
            self._pending_frame = None

            process = self._process
            self._process = None

        if process is not None:
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass

            try:
                returncode = process.wait(
                    timeout=30.0,
                )

            except subprocess.TimeoutExpired as exc:
                process.kill()
                _ = process.wait()

                failure = RecordingError("FFmpeg did not finish within 30 seconds")

                with self._lock:
                    self._last_error = failure

                raise failure from exc

            error = ""

            stderr = cast(
                BinaryIO | None,
                process.stderr,
            )

            if stderr is not None:
                stderr_data: bytes = stderr.read()

                error = stderr_data.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

            if returncode != 0:
                failure = RecordingError(
                    "FFmpeg failed" + (f": {error}" if error else "")
                )

                with self._lock:
                    self._last_error = failure

                raise failure

        with self._lock:
            last_error = self._last_error
            path = self._path
            start_timestamp = self._start_timestamp
            end_timestamp = self._end_timestamp
            frame_count = self._frame_count

        if last_error is not None:
            raise RecordingError(f"recording failed: {last_error}") from last_error

        if path is None or start_timestamp is None:
            raise RecordingError("recording stopped before any frames were captured")

        final_timestamp = start_timestamp if end_timestamp is None else end_timestamp

        return Recording(
            path=path,
            start_timestamp=start_timestamp,
            end_timestamp=final_timestamp,
            frame_count=frame_count,
            fps=self.fps,
        )

    def stop_data(self) -> RecordingData:
        recording = self.stop()

        try:
            data = recording.path.read_bytes()
        finally:
            try:
                recording.path.unlink()
            except FileNotFoundError:
                pass

        return RecordingData(
            data=data,
            format="mp4",
            start_timestamp=recording.start_timestamp,
            end_timestamp=recording.end_timestamp,
            frame_count=recording.frame_count,
            fps=recording.fps,
        )

    def is_recording(self) -> bool:
        with self._frame_condition:
            return self._recording

    def last_error(self) -> RecordingError | None:
        with self._frame_condition:
            return self._last_error

    @override
    def on_frame(
        self,
        frame: Frame,
    ) -> None:
        with self._frame_condition:
            if not self._recording:
                return

            self._pending_frame = frame
            self._frame_condition.notify_all()

    def _recording_loop(self) -> None:
        while True:
            with self._frame_condition:
                while self._recording and self._pending_frame is None:
                    _ = self._frame_condition.wait()

                if not self._recording and self._pending_frame is None:
                    return

                frame = self._pending_frame
                self._pending_frame = None

            if frame is None:
                continue

            try:
                self._write_frame(frame)

            except RecordingError as exc:
                with self._frame_condition:
                    self._last_error = exc
                    self._recording = False
                    self._pending_frame = None
                    self._frame_condition.notify_all()

                self._abort_encoder()
                return

    def _write_frame(
        self,
        frame: Frame,
    ) -> None:
        image = frame.image

        if image.ndim != 3 or image.shape[2] != 3:
            raise RecordingError("recording requires a 3-channel image")

        height, width = image.shape[:2]
        size = (width, height)

        if self._process is None:
            self._open_encoder(
                size,
                frame.timestamp,
            )

        if self._size != size:
            raise RecordingError("frame size changed during recording")

        if self.overlay_enabled and self.metadata_bus is not None:
            metadata = self.metadata_bus.latest(self.overlay_source)

            if metadata is not None:
                try:
                    frame = self.overlay.draw_metadata(frame, metadata)
                except OverlayError:
                    pass

        image = frame.image

        try:
            image = cast(
                ImageArray,
                cast(
                    object,
                    cv2.cvtColor(
                        image,
                        cv2.COLOR_RGB2BGR,
                    ),
                ),
            )
        except cv2.error as exc:
            raise RecordingError(f"failed to prepare recording frame: {exc}") from exc

        process = self._process

        if process is None or process.stdin is None:
            raise RecordingError("FFmpeg encoder is not available")

        try:
            _ = process.stdin.write(image.tobytes())

        except BrokenPipeError as exc:
            error = ""

            stderr = cast(
                BinaryIO | None,
                process.stderr,
            )

            if stderr is not None:
                stderr_data: bytes = stderr.read()

                error = stderr_data.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

            raise RecordingError(
                "FFmpeg stopped accepting frames" + (f": {error}" if error else "")
            ) from exc

        self._frame_count += 1
        self._end_timestamp = frame.timestamp

    def enable_overlay(
        self,
        source: str | None = None,
    ) -> None:
        if source is not None:
            source = source.strip()

            if not source:
                raise ValueError("source cannot be empty")

        self.overlay_enabled = True
        self.overlay_source = source

    def disable_overlay(self) -> None:
        self.overlay_enabled = False
        self.overlay_source = None

    def overlay_status(self) -> dict[str, str | bool | None]:
        return {
            "enabled": self.overlay_enabled,
            "source": self.overlay_source,
        }

    def _open_encoder(
        self,
        size: tuple[int, int],
        timestamp: float,
    ) -> None:
        if self._path is None:
            raise RecordingError("recording path has not been initialized")

        width, height = size

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-video_size",
            f"{width}x{height}",
            "-framerate",
            str(self.fps),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(self._path),
        ]

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

        except OSError as exc:
            raise RecordingError(f"failed to start FFmpeg: {exc}") from exc

        if process.stdin is None:
            process.kill()
            _ = process.wait()

            raise RecordingError("failed to open FFmpeg input pipe")

        self._process = process
        self._size = size
        self._start_timestamp = timestamp
        self._end_timestamp = timestamp

    def _abort_encoder(self) -> None:
        process = self._process
        self._process = None

        if process is None:
            return

        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass

        if process.poll() is None:
            process.kill()

        try:
            _ = process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            _ = process.wait()
