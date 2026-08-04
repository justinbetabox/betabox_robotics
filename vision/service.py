from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from betabox_robotics.vision.detection import DetectionManager
from betabox_robotics.vision.detectors.color import HSVRangeInput
from betabox_robotics.vision.frame_source import FrameSource, FrameSourceError
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer
from betabox_robotics.vision.recording import (
    Recording,
    RecordingData,
    RecordingError,
    RecordingService,
)
from betabox_robotics.vision.signaling import WebRTCSignalingServer
from betabox_robotics.vision.snapshot import (
    ImageFormat,
    Snapshot,
    SnapshotData,
    SnapshotService,
)
from betabox_robotics.vision.stream import StreamError
from betabox_robotics.vision.webrtc import WebRTCStreamer


@dataclass(frozen=True, slots=True)
class VisionServiceConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    fps: int = 20

    def __post_init__(self) -> None:
        if not isinstance(self.host, str):
            raise TypeError("host must be a string")

        host = self.host.strip()

        if not host:
            raise ValueError("host cannot be empty")

        if isinstance(self.port, bool) or not isinstance(
            self.port,
            int,
        ):
            raise TypeError("port must be an integer")

        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")

        if isinstance(self.fps, bool) or not isinstance(
            self.fps,
            int,
        ):
            raise TypeError("fps must be an integer")

        if self.fps <= 0:
            raise ValueError("fps must be greater than zero")

        object.__setattr__(
            self,
            "host",
            host,
        )


class VisionService:
    """
    Owns the camera frame pipeline for managed Betabox video streaming.

    This service is intended to be the single owner of the physical camera
    when running as betabox-video.service.
    """

    def __init__(
        self,
        config: VisionServiceConfig | None = None,
    ) -> None:
        if config is not None and not isinstance(
            config,
            VisionServiceConfig,
        ):
            raise TypeError("config must be a VisionServiceConfig")

        self.config = config if config is not None else VisionServiceConfig()

        self.frame_source = FrameSource(
            fps=self.config.fps,
        )

        self.metadata_bus = MetadataBus()
        self.overlay = OverlayRenderer()

        self.detection = DetectionManager(
            self.metadata_bus,
        )

        self.recording = RecordingService(
            fps=self.config.fps,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )

        self.streamer = WebRTCStreamer(
            fps=self.config.fps,
            metadata_bus=self.metadata_bus,
            overlay=self.overlay,
        )

        self.snapshot = SnapshotService(
            self.frame_source,
        )

        self.frame_source.register_consumer(
            self.detection,
        )
        self.frame_source.register_consumer(
            self.recording,
        )
        self.frame_source.register_consumer(
            self.streamer,
        )

        self.server = WebRTCSignalingServer(
            self,
            host=self.config.host,
            port=self.config.port,
        )

        self._running = False

    def start(self) -> None:
        if self._running:
            return

        self.frame_source.start()

        try:
            self.streamer.start()
        except StreamError:
            try:
                self.frame_source.stop()
            except FrameSourceError:
                pass

            raise

        self._running = True

    def run(self) -> None:
        self.start()
        self.server.run()

    def stop(self) -> None:
        """
        Stop the local Vision pipeline.

        Active WebRTC peers are normally closed by the signaling server's
        aiohttp shutdown hook before this synchronous pipeline shutdown runs.
        """
        if not self._running:
            return

        shutdown_error: Exception | None = None

        try:
            try:
                self.streamer.stop()
            except StreamError as exc:
                shutdown_error = exc

            if self.recording.is_recording():
                try:
                    recording = self.recording.stop()
                except RecordingError as exc:
                    if shutdown_error is None:
                        shutdown_error = exc
                else:
                    try:
                        recording.path.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError as exc:
                        if shutdown_error is None:
                            shutdown_error = exc

        finally:
            try:
                self.frame_source.stop()
            except FrameSourceError as exc:
                if shutdown_error is None:
                    shutdown_error = exc
            finally:
                self._running = False

        if shutdown_error is not None:
            raise shutdown_error

    def statistics(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "camera": self.frame_source.statistics(),
            "streaming": self.streamer.statistics(),
            "recording": {
                "active": self.recording.is_recording(),
                "overlay": self.recording_overlay_status(),
            },
            "detection": {
                "detectors": self.detection_status(),
                "metadata_sources": list(self.metadata_bus.all_latest().keys()),
            },
            "server": {
                "host": self.config.host,
                "port": self.config.port,
                "fps": self.config.fps,
            },
        }

    def close(self) -> None:
        self.stop()

    def capture_snapshot(
        self,
        *,
        filename: str | None = None,
        directory: str | Path | None = None,
        image_format: ImageFormat | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> Snapshot:
        if not overlay:
            return self.snapshot.capture(
                filename=filename,
                directory=directory,
                image_format=image_format,
            )

        frame = self.frame_source.latest_frame()
        metadata = self.latest_metadata(source)

        if metadata is not None:
            frame = self.overlay.draw_metadata(
                frame,
                metadata,
            )

        return self.snapshot.capture_frame(
            frame,
            filename=filename,
            directory=directory,
            image_format=image_format,
        )

    def capture_snapshot_data(
        self,
        *,
        overlay: bool = False,
        source: str | None = None,
        image_format: ImageFormat | None = None,
    ) -> SnapshotData:
        if not overlay:
            return self.snapshot.capture_data(
                image_format=image_format,
            )

        frame = self.frame_source.latest_frame()
        metadata = self.latest_metadata(source)

        if metadata is not None:
            frame = self.overlay.draw_metadata(
                frame,
                metadata,
            )

        return self.snapshot.capture_frame_data(
            frame,
            image_format=image_format,
        )

    def start_recording(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> Path:
        if overlay:
            self.enable_recording_overlay(source)
        else:
            self.disable_recording_overlay()

        return self.recording.start(filename=filename)

    def stop_recording(self) -> Recording:
        return self.recording.stop()

    def stop_recording_data(self) -> RecordingData:
        return self.recording.stop_data()

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

    def enable_detection(self, name: str) -> None:
        self.detection.enable(name)

    def disable_detection(self, name: str) -> None:
        self.detection.disable(name)

    def detection_names(self) -> list[str]:
        return self.detection.names()

    def detection_status(self) -> dict[str, bool]:
        return {
            name: self.detection.is_enabled(name) for name in self.detection.names()
        }

    def enable_stream_overlay(self, source: str | None = None) -> None:
        self.streamer.enable_overlay(source)

    def disable_stream_overlay(self) -> None:
        self.streamer.disable_overlay()

    def stream_overlay_status(self) -> dict[str, bool | str | None]:
        return self.streamer.overlay_status()

    def enable_recording_overlay(self, source: str | None = None) -> None:
        self.recording.enable_overlay(source)

    def disable_recording_overlay(self) -> None:
        self.recording.disable_overlay()

    def recording_overlay_status(self) -> dict[str, bool | str | None]:
        return self.recording.overlay_status()

    def latest_metadata(self, source: str | None = None) -> Metadata | None:
        return self.metadata_bus.latest(source)

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.stop()
