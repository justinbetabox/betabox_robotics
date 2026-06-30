from dataclasses import dataclass
from pathlib import Path
from time import strftime
from typing import Literal

import cv2

from betabox_car.vision.frame import Frame
from betabox_car.vision.frame_source import FrameSourceError
from betabox_car.vision.interfaces import FrameProvider

ImageFormat = Literal["jpg", "jpeg", "png"]


@dataclass(frozen=True)
class Snapshot:
    path: Path
    timestamp: float
    format: str


class SnapshotError(FrameSourceError):
    """Raised when snapshot operations fail."""


class SnapshotService:
    """
    Saves still images from the existing Vision frame pipeline.

    SnapshotService does not own or open the camera. It uses a frame
    provider that exposes the latest available frame.
    """

    def __init__(
        self,
        frame_source: FrameProvider,
        *,
        directory: str | Path = Path.home() / "media" / "pictures",
        default_format: ImageFormat = "jpg",
    ) -> None:
        self.frame_source = frame_source
        self.directory = Path(directory)
        self.default_format = default_format

    def capture(
        self,
        *,
        filename: str | None = None,
        directory: str | Path | None = None,
        image_format: ImageFormat | None = None,
    ) -> Snapshot:
        frame = self.frame_source.latest_frame()
        output_dir = Path(directory) if directory is not None else self.directory
        fmt = image_format or self.default_format

        if fmt == "jpeg":
            fmt = "jpg"

        if fmt not in ("jpg", "png"):
            raise SnapshotError(f"unsupported snapshot format: {fmt}")

        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = f"snapshot_{strftime('%Y%m%d_%H%M%S')}.{fmt}"

        path = output_dir / filename

        if path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            path = path.with_suffix(f".{fmt}")

        self._write_frame(frame, path)

        return Snapshot(
            path=path,
            timestamp=frame.timestamp,
            format=fmt,
        )

    def _write_frame(self, frame: Frame, path: Path) -> None:
        image = frame.image

        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        success = cv2.imwrite(str(path), image)

        if not success:
            raise SnapshotError(f"failed to write snapshot: {path}")
