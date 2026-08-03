from dataclasses import dataclass
from pathlib import Path
from time import strftime
from typing import Literal

import cv2

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import FrameSourceError
from betabox_robotics.vision.interfaces import FrameProvider

ImageFormat = Literal["jpg", "jpeg", "png"]

NormalizedImageFormat = Literal["jpg", "png"]


@dataclass(frozen=True, slots=True)
class Snapshot:
    path: Path
    timestamp: float
    format: NormalizedImageFormat


@dataclass(frozen=True, slots=True)
class SnapshotData:
    data: bytes
    timestamp: float
    format: NormalizedImageFormat


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
        fmt = default_format.lower()

        if fmt == "jpeg":
            fmt = "jpg"

        if fmt not in ("jpg", "png"):
            raise ValueError(f"unsupported snapshot format: {default_format}")

        self.default_format: NormalizedImageFormat = fmt

    def _normalize_format(
        self,
        image_format: ImageFormat | None,
    ) -> NormalizedImageFormat:
        fmt = (image_format or self.default_format).lower()

        if fmt == "jpeg":
            fmt = "jpg"

        if fmt not in ("jpg", "png"):
            raise SnapshotError(f"unsupported snapshot format: {fmt}")

        return fmt

    def capture(
        self,
        *,
        filename: str | None = None,
        directory: str | Path | None = None,
        image_format: ImageFormat | None = None,
    ) -> Snapshot:
        frame = self.frame_source.latest_frame()
        return self.capture_frame(
            frame,
            filename=filename,
            directory=directory,
            image_format=image_format,
        )

    def capture_data(
        self,
        *,
        image_format: ImageFormat | None = None,
    ) -> SnapshotData:
        frame = self.frame_source.latest_frame()
        return self.capture_frame_data(
            frame,
            image_format=image_format,
        )

    def capture_frame_data(
        self,
        frame: Frame,
        *,
        image_format: ImageFormat | None = None,
    ) -> SnapshotData:
        fmt = self._normalize_format(image_format)

        image = frame.image

        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(
                image,
                cv2.COLOR_RGB2BGR,
            )

        try:
            success, encoded = cv2.imencode(
                f".{fmt}",
                image,
            )
        except cv2.error as exc:
            raise SnapshotError(f"failed to encode snapshot as {fmt}") from exc

        if not success:
            raise SnapshotError(f"failed to encode snapshot as {fmt}")

        return SnapshotData(
            data=encoded.tobytes(),
            timestamp=frame.timestamp,
            format=fmt,
        )

    def capture_frame(
        self,
        frame: Frame,
        *,
        filename: str | None = None,
        directory: str | Path | None = None,
        image_format: ImageFormat | None = None,
    ) -> Snapshot:
        output_dir = Path(directory) if directory is not None else self.directory
        fmt = self._normalize_format(image_format)

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SnapshotError(
                f"failed to create snapshot directory: {output_dir}"
            ) from exc

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

        try:
            success = cv2.imwrite(str(path), image)
        except cv2.error as exc:
            raise SnapshotError(f"failed to write snapshot: {path}") from exc

        if not success:
            raise SnapshotError(f"failed to write snapshot: {path}")
