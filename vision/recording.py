import threading
from dataclasses import dataclass
from pathlib import Path
from time import strftime
from typing import Optional

import cv2

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import FrameSourceError


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
    ) -> None:
        if fps <= 0:
            raise RecordingError("fps must be greater than 0")

        self.directory = Path(directory)
        self.fps = float(fps)
        self.filename_prefix = filename_prefix

        self._writer: Optional[cv2.VideoWriter] = None
        self._path: Optional[Path] = None
        self._start_timestamp: Optional[float] = None
        self._end_timestamp: Optional[float] = None
        self._frame_count = 0
        self._recording = False
        self._size: Optional[tuple[int, int]] = None
        self._lock = threading.Lock()

    def start(self, *, filename: str | None = None) -> Path:
        with self._lock:
            if self._recording:
                raise RecordingError("recording is already running")

            self.directory.mkdir(parents=True, exist_ok=True)

            if filename is None:
                filename = f"{self.filename_prefix}_{strftime('%Y%m%d_%H%M%S')}.mp4"

            path = self.directory / filename

            if path.suffix.lower() != ".mp4":
                path = path.with_suffix(".mp4")

            self._path = path
            self._writer = None
            self._start_timestamp = None
            self._end_timestamp = None
            self._frame_count = 0
            self._size = None
            self._recording = True

            return path

    def stop(self) -> Recording:
        with self._lock:
            if not self._recording:
                raise RecordingError("recording is not running")

            self._recording = False

            if self._writer is not None:
                self._writer.release()
                self._writer = None

            if self._path is None or self._start_timestamp is None:
                raise RecordingError(
                    "recording stopped before any frames were captured"
                )

            end_timestamp = self._end_timestamp or self._start_timestamp

            return Recording(
                path=self._path,
                start_timestamp=self._start_timestamp,
                end_timestamp=end_timestamp,
                frame_count=self._frame_count,
                fps=self.fps,
            )

    def is_recording(self) -> bool:
        return self._recording

    def on_frame(self, frame: Frame) -> None:
        with self._lock:
            if not self._recording:
                return

            image = frame.image

            if len(image.shape) != 3 or image.shape[2] != 3:
                raise RecordingError("recording requires a 3-channel image")

            height, width = image.shape[:2]
            size = (width, height)

            if self._writer is None:
                self._open_writer(size, frame.timestamp)

            if self._size != size:
                raise RecordingError("frame size changed during recording")

            # OpenCV writes BGR frames. Vision frames are RGB.
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            assert self._writer is not None
            self._writer.write(image)

            self._frame_count += 1
            self._end_timestamp = frame.timestamp

    def _open_writer(self, size: tuple[int, int], timestamp: float) -> None:
        if self._path is None:
            raise RecordingError("recording path has not been initialized")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(self._path), fourcc, self.fps, size)

        if not writer.isOpened():
            raise RecordingError(f"failed to open recording writer: {self._path}")

        self._writer = writer
        self._size = size
        self._start_timestamp = timestamp
        self._end_timestamp = timestamp
