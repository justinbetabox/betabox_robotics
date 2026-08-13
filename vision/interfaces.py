from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, Protocol

from betabox_robotics.vision.detectors.color import HSVRangeInput
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.webrtc import WebRTCStreamer

ImageFormat = Literal[
    "jpg",
    "jpeg",
    "png",
]


class SnapshotDataInterface(Protocol):
    data: bytes
    timestamp: float
    format: Literal[
        "jpg",
        "png",
    ]


class RecordingDataInterface(Protocol):
    data: bytes
    start_timestamp: float
    end_timestamp: float
    frame_count: int
    fps: float
    format: str


class FrameProvider(Protocol):
    """
    Structural interface for objects that expose the latest available frame.

    Implementations do not necessarily own the camera. They may provide a
    frame cached by any part of the Vision pipeline.
    """

    def latest_frame(self) -> Frame:
        """Return the latest available frame."""
        ...


class VisionServiceInterface(Protocol):
    """Interface required by the WebRTC signaling server."""

    streamer: WebRTCStreamer

    def statistics(
        self,
    ) -> object: ...

    def capture_snapshot_data(
        self,
        *,
        overlay: bool = False,
        source: str | None = None,
        image_format: ImageFormat | None = None,
    ) -> SnapshotDataInterface: ...

    def start_recording(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> Path: ...

    def stop_recording_data(
        self,
    ) -> RecordingDataInterface: ...

    def latest_metadata(
        self,
        source: str | None = None,
    ) -> Metadata | None: ...

    def detection_names(
        self,
    ) -> list[str]: ...

    def detection_status(
        self,
    ) -> dict[str, bool]: ...

    def enable_detection(
        self,
        name: str,
    ) -> None: ...

    def disable_detection(
        self,
        name: str,
    ) -> None: ...

    def enable_color_detection(
        self,
        colors: str | Sequence[str] | None = None,
        *,
        custom_ranges: Mapping[
            str,
            HSVRangeInput,
        ]
        | None = None,
        min_area: float | None = None,
    ) -> None: ...

    def enable_stream_overlay(
        self,
        source: str | None = None,
    ) -> None: ...

    def disable_stream_overlay(
        self,
    ) -> None: ...

    def stream_overlay_status(
        self,
    ) -> dict[str, bool | str | None]: ...
