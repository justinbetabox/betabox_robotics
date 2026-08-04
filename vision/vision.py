from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Self

from betabox_robotics.vision.consumer import FrameConsumer
from betabox_robotics.vision.detection import DetectionManager
from betabox_robotics.vision.detectors.color import (
    HSVRangeInput,
)
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.frame_source import (
    FrameSource,
    FrameSourceError,
)
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer
from betabox_robotics.vision.recording import (
    RecordingError,
    RecordingService,
)
from betabox_robotics.vision.snapshot import SnapshotService


class Vision:
    """
    Direct Vision subsystem container.

    This subsystem owns a FrameSource and therefore opens the physical
    camera. Use it only when the managed betabox-video.service is not
    running.

    Long-running platform video should use VisionService instead.
    """

    def __init__(
        self,
        frame_source: FrameSource | None = None,
        metadata_bus: MetadataBus | None = None,
    ) -> None:
        if frame_source is not None and not isinstance(
            frame_source,
            FrameSource,
        ):
            raise TypeError("frame_source must be a FrameSource")

        if metadata_bus is not None and not isinstance(
            metadata_bus,
            MetadataBus,
        ):
            raise TypeError("metadata_bus must be a MetadataBus")

        self.frame_source = frame_source if frame_source is not None else FrameSource()

        self.metadata = metadata_bus if metadata_bus is not None else MetadataBus()

        self.overlay = OverlayRenderer()
        self.detection = DetectionManager(self.metadata)
        self.snapshot = SnapshotService(self.frame_source)
        self.recording = RecordingService(
            fps=self.frame_source.fps,
            metadata_bus=self.metadata,
            overlay=self.overlay,
        )

        self.register_consumer(self.recording)
        self.register_consumer(self.detection)

    @classmethod
    def default(
        cls,
        robot_config: object | None = None,
    ) -> Self:
        return cls()

    def start(self) -> None:
        self.frame_source.start()

    def stop(self) -> None:
        shutdown_error: RecordingError | FrameSourceError | None = None

        if self.recording.is_recording():
            try:
                self.recording.stop()
            except RecordingError as exc:
                shutdown_error = exc

        try:
            self.frame_source.stop()
        except FrameSourceError as exc:
            if shutdown_error is None:
                shutdown_error = exc

        if shutdown_error is not None:
            raise shutdown_error

    def enable_detection(
        self,
        name: str,
    ) -> None:
        self.detection.enable(name)

    def disable_detection(
        self,
        name: str,
    ) -> None:
        self.detection.disable(name)

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
    ) -> None:
        self.detection.enable_color(
            colors,
            custom_ranges=custom_ranges,
            min_area=min_area,
        )

    def disable_color_detection(self) -> None:
        self.disable_detection("color")

    def detection_names(self) -> list[str]:
        return self.detection.names()

    def detection_status(self) -> dict[str, bool]:
        return {
            name: self.detection.is_enabled(name) for name in self.detection.names()
        }

    def latest_metadata(
        self,
        source: str | None = None,
    ) -> Metadata | None:
        return self.metadata.latest(source)

    def is_running(self) -> bool:
        return self.frame_source.is_running()

    def latest_frame(self) -> Frame:
        return self.frame_source.latest_frame()

    def register_consumer(
        self,
        consumer: FrameConsumer,
    ) -> None:
        self.frame_source.register_consumer(consumer)

    def unregister_consumer(
        self,
        consumer: FrameConsumer,
    ) -> None:
        self.frame_source.unregister_consumer(consumer)

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
