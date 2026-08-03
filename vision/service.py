from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from betabox_robotics.vision.detection import DetectionManager
from betabox_robotics.vision.frame_source import FrameSource
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer
from betabox_robotics.vision.recording import (
    Recording,
    RecordingData,
    RecordingService,
)
from betabox_robotics.vision.signaling import WebRTCSignalingServer
from betabox_robotics.vision.snapshot import Snapshot, SnapshotData, SnapshotService
from betabox_robotics.vision.webrtc import WebRTCStreamer


@dataclass(frozen=True, slots=True)
class VisionServiceConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    fps: int = 20

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("host cannot be empty")

        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")

        if self.fps <= 0:
            raise ValueError("fps must be greater than zero")


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
        self.config = config or VisionServiceConfig()

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
        except Exception:
            self.frame_source.stop()
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

        error: Exception | None = None

        try:
            self.streamer.stop()

            if self.recording.is_recording():
                try:
                    recording = self.recording.stop()
                except Exception as exc:
                    error = exc
                else:
                    try:
                        recording.path.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError as exc:
                        error = exc

        finally:
            try:
                self.frame_source.stop()
            finally:
                self._running = False

        if error is not None:
            raise error

    def statistics(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "camera": self.frame_source.statistics(),
            "streaming": {
                **self.streamer.statistics(),
                "overlay": self.stream_overlay_status(),
            },
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
        overlay: bool = False,
        source: str | None = None,
        **kwargs,
    ) -> Snapshot:
        if not overlay:
            return self.snapshot.capture(**kwargs)

        frame = self.frame_source.latest_frame()
        metadata = self.latest_metadata(source)

        if metadata is not None:
            frame = self.overlay.draw_metadata(
                frame,
                metadata,
            )

        return self.snapshot.capture_frame(
            frame,
            **kwargs,
        )

    def capture_snapshot_data(
        self,
        *,
        overlay: bool = False,
        source: str | None = None,
        image_format: str | None = None,
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
        min_area: float | None = None,
    ) -> None:
        self.detection.enable_color(
            colors,
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

    def __enter__(self) -> VisionService:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
