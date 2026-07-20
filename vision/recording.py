import shutil
import subprocess
import tempfile
import threading

from dataclasses import dataclass
from pathlib import Path
from time import strftime
from typing import Optional

import cv2

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import FrameSourceError
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer


@dataclass(frozen=True)
class Recording:
    path: Path
    start_timestamp: float
    end_timestamp: float
    frame_count: int
    fps: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_timestamp - self.start_timestamp)


class RecordingError(FrameSourceError):
    """Raised when recording operations fail."""


class RecordingService(FrameConsumer):
    """
    Records frames from the Vision frame pipeline.

    RecordingService does not own or open the camera. It is registered
    as a FrameConsumer with FrameSource while recording.
    """

    def __init__(
        self,
        *,
        directory: str | Path = Path.home() / "media" / "videos",
        fps: float = 20.0,
        filename_prefix: str = "recording",
        metadata_bus: MetadataBus | None = None,
        overlay: OverlayRenderer | None = None,
    ) -> None:
        if fps <= 0:
            raise RecordingError("fps must be greater than 0")

        self.directory = Path(directory)
        self.fps = float(fps)
        self.filename_prefix = filename_prefix
        self.metadata_bus = metadata_bus
        self.overlay = overlay or OverlayRenderer()
        self.overlay_enabled = False
        self.overlay_source: str | None = None

        self._process: subprocess.Popen[bytes] | None = None
        self._path: Optional[Path] = None
        self._last_error: Exception | None = None
        self._start_timestamp: Optional[float] = None
        self._end_timestamp: Optional[float] = None
        self._frame_count = 0
        self._recording = False
        self._size: Optional[tuple[int, int]] = None
        self._lock = threading.Lock()

    def start(
        self,
        *,
        filename: str | None = None,
    ) -> Path:
        with self._lock:
            if self._recording:
                raise RecordingError(
                    "recording is already running"
                )

            if shutil.which("ffmpeg") is None:
                raise RecordingError(
                    "ffmpeg is not installed"
                )

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
                    "recording directory is not writable: "
                    f"{self.directory}: {exc}"
                ) from exc

            if filename is None:
                filename = (
                    f"{self.filename_prefix}_"
                    f"{strftime('%Y%m%d_%H%M%S')}.mp4"
                )
            else:
                filename_path = Path(filename)

                if (
                    not filename
                    or filename_path.name != filename
                ):
                    raise RecordingError(
                        "recording filename must be a plain "
                        "filename without directory components"
                    )

            path = self.directory / filename

            if path.suffix.lower() != ".mp4":
                path = path.with_suffix(".mp4")

            self._path = path
            self._process = None
            self._last_error = None
            self._start_timestamp = None
            self._end_timestamp = None
            self._frame_count = 0
            self._size = None
            self._recording = True

            return path

    def stop(self) -> Recording:
        with self._lock:
            if not self._recording:
                if self._last_error is not None:
                    raise RecordingError(
                        f"recording failed: {self._last_error}"
                    ) from self._last_error

                raise RecordingError(
                    "recording is not running"
                )

            self._recording = False

            process = self._process
            self._process = None

            if process is not None:
                if process.stdin is not None:
                    process.stdin.close()

                try:
                    returncode = process.wait(
                        timeout=30.0,
                    )

                except subprocess.TimeoutExpired as exc:
                    process.kill()
                    process.wait()

                    failure = RecordingError(
                        "FFmpeg did not finish within 30 seconds"
                    )

                    self._last_error = failure
                    raise failure from exc

                error = ""

                if process.stderr is not None:
                    error = (
                        process.stderr.read()
                        .decode(
                            "utf-8",
                            errors="replace",
                        )
                        .strip()
                    )

                if returncode != 0:
                    failure = RecordingError(
                        "FFmpeg failed"
                        + (
                            f": {error}"
                            if error
                            else ""
                        )
                    )

                    self._last_error = failure
                    raise failure

            if (
                self._path is None
                or self._start_timestamp is None
            ):
                if self._last_error is not None:
                    raise RecordingError(
                        "recording failed before the first "
                        f"frame: {self._last_error}"
                    ) from self._last_error

                raise RecordingError(
                    "recording stopped before any frames "
                    "were captured"
                )

            end_timestamp = (
                self._end_timestamp
                or self._start_timestamp
            )

            return Recording(
                path=self._path,
                start_timestamp=self._start_timestamp,
                end_timestamp=end_timestamp,
                frame_count=self._frame_count,
                fps=self.fps,
            )

    def is_recording(self) -> bool:
        return self._recording

    def last_error(self) -> Exception | None:
        return self._last_error

    def on_frame(
        self,
        frame: Frame,
    ) -> None:
        with self._lock:
            if not self._recording:
                return

            try:
                self._write_frame(frame)

            except Exception as exc:
                self._last_error = exc
                self._recording = False
                self._abort_encoder()
                raise

    def _write_frame(
        self,
        frame: Frame,
    ) -> None:
        image = frame.image

        if (
            len(image.shape) != 3
            or image.shape[2] != 3
        ):
            raise RecordingError(
                "recording requires a 3-channel image"
            )

        height, width = image.shape[:2]
        size = (width, height)

        if self._process is None:
            self._open_encoder(
                size,
                frame.timestamp,
            )

        if self._size != size:
            raise RecordingError(
                "frame size changed during recording"
            )

        if (
            self.overlay_enabled
            and self.metadata_bus is not None
        ):
            metadata = self.metadata_bus.latest(
                self.overlay_source
            )

            if metadata is not None:
                frame = self.overlay.draw_metadata(
                    frame,
                    metadata,
                )

        image = frame.image

        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2BGR,
        )

        assert self._process is not None
        assert self._process.stdin is not None

        try:
            self._process.stdin.write(
                image.tobytes()
            )

        except BrokenPipeError as exc:
            error = ""

            if self._process.stderr is not None:
                error = (
                    self._process.stderr.read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                    .strip()
                )

            raise RecordingError(
                "FFmpeg stopped accepting frames"
                + (
                    f": {error}"
                    if error
                    else ""
                )
            ) from exc

        self._frame_count += 1
        self._end_timestamp = frame.timestamp

    def enable_overlay(self, source: str | None = None) -> None:
        self.overlay_enabled = True
        self.overlay_source = source

    def disable_overlay(self) -> None:
        self.overlay_enabled = False
        self.overlay_source = None

    def overlay_status(self) -> dict:
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
            raise RecordingError(
                "recording path has not been initialized"
            )

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
            raise RecordingError(
                f"failed to start FFmpeg: {exc}"
            ) from exc

        if process.stdin is None:
            process.kill()
            process.wait()

            raise RecordingError(
                "failed to open FFmpeg input pipe"
            )

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
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
