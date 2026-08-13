from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import strftime
from typing import Literal, cast

import cv2

from betabox_robotics.vision.frame import Frame, ImageArray
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


def normalize_image_format(
    value: object,
) -> NormalizedImageFormat:
    if not isinstance(value, str):
        raise TypeError("image format must be a string")

    image_format = value.strip().casefold()

    if not image_format:
        raise ValueError("image format cannot be empty")

    if image_format in {
        "jpg",
        "jpeg",
    }:
        return "jpg"

    if image_format == "png":
        return "png"

    raise ValueError(f"unsupported snapshot format: {value}")


def _validate_directory(
    value: object,
    *,
    name: str,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string or Path")

    return Path(value).expanduser()


def _validate_filename(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("filename must be a string")

    filename = value.strip()

    if not filename:
        raise ValueError("filename cannot be empty")

    path = Path(filename)

    if path.name != filename:
        raise ValueError("filename must not contain a directory")

    return filename


class SnapshotService:
    """
    Save still images from the existing Vision frame pipeline.

    SnapshotService does not own or open the camera. It uses a frame
    provider that exposes the latest available frame.
    """

    frame_source: FrameProvider
    directory: Path
    default_format: NormalizedImageFormat

    def __init__(
        self,
        frame_source: FrameProvider,
        *,
        directory: str | Path | None = None,
        default_format: ImageFormat = "jpg",
    ) -> None:
        self.frame_source = frame_source

        self.directory = (
            Path.home() / "media" / "pictures"
            if directory is None
            else _validate_directory(
                directory,
                name="directory",
            )
        )

        self.default_format = normalize_image_format(default_format)

    def _normalize_format(
        self,
        image_format: ImageFormat | None,
    ) -> NormalizedImageFormat:
        if image_format is None:
            return self.default_format

        return normalize_image_format(image_format)

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
        image = self._prepare_image(frame)
        image_format_value = self._normalize_format(image_format)

        try:
            success, encoded = cv2.imencode(
                f".{image_format_value}",
                image,
            )
        except cv2.error as exc:
            raise SnapshotError(
                f"failed to encode snapshot as {image_format_value}: {exc}"
            ) from exc

        if not success:
            raise SnapshotError(f"failed to encode snapshot as {image_format_value}")

        return SnapshotData(
            data=encoded.tobytes(),
            timestamp=frame.timestamp,
            format=image_format_value,
        )

    def capture_frame(
        self,
        frame: Frame,
        *,
        filename: str | None = None,
        directory: str | Path | None = None,
        image_format: ImageFormat | None = None,
    ) -> Snapshot:
        output_directory = (
            self.directory
            if directory is None
            else _validate_directory(
                directory,
                name="directory",
            )
        )

        image_format_value = self._normalize_format(image_format)

        try:
            output_directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise SnapshotError(
                f"failed to create snapshot directory: {output_directory}"
            ) from exc

        if filename is None:
            filename_value = (
                f"snapshot_{strftime('%Y%m%d_%H%M%S')}.{image_format_value}"
            )
        else:
            filename_value = _validate_filename(filename)

        path = (output_directory / filename_value).with_suffix(f".{image_format_value}")

        self._write_frame(
            frame,
            path,
        )

        return Snapshot(
            path=path,
            timestamp=frame.timestamp,
            format=image_format_value,
        )

    def _prepare_image(
        self,
        frame: Frame,
    ) -> ImageArray:
        image = frame.image

        if image.ndim not in {
            2,
            3,
        }:
            raise SnapshotError("snapshot image must be two- or three-dimensional")

        if image.ndim == 3 and image.shape[2] not in {
            1,
            3,
            4,
        }:
            raise SnapshotError("snapshot image has an unsupported channel count")

        try:
            if image.ndim == 3 and image.shape[2] == 3:
                return cast(
                    ImageArray,
                    cast(
                        object,
                        cv2.cvtColor(
                            image,
                            cv2.COLOR_RGB2BGR,
                        ),
                    ),
                )

            if image.ndim == 3 and image.shape[2] == 4:
                return cast(
                    ImageArray,
                    cast(
                        object,
                        cv2.cvtColor(
                            image,
                            cv2.COLOR_RGBA2BGRA,
                        ),
                    ),
                )

        except cv2.error as exc:
            raise SnapshotError(f"failed to prepare snapshot image: {exc}") from exc

        return image

    def _write_frame(
        self,
        frame: Frame,
        path: Path,
    ) -> None:
        image = self._prepare_image(frame)

        try:
            success = cv2.imwrite(
                str(path),
                image,
            )
        except cv2.error as exc:
            raise SnapshotError(f"failed to write snapshot: {path}") from exc

        if not success:
            raise SnapshotError(f"failed to write snapshot: {path}")
