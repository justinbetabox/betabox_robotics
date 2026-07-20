from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.vision.detection import DetectionManager
from betabox_robotics.vision.frame_source import FrameSource
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.recording import Recording, RecordingService
from betabox_robotics.vision.signaling import WebRTCSignalingServer
from betabox_robotics.vision.snapshot import Snapshot, SnapshotService
from betabox_robotics.vision.webrtc import WebRTCStreamer
from betabox_robotics.vision.overlay import OverlayRenderer


@dataclass(frozen=True)
class VisionServiceConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    fps: int = 20


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
        self.config = (
            config
            or VisionServiceConfig()
        )

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
        self.streamer.start()
        self._running = True

    def run(self) -> None:
        self.start()
        self.server.run()

    def stop(self) -> None:
        if not self._running:
            return

        self.streamer.stop()

        if self.recording.is_recording():
            self.recording.stop()

        self.frame_source.stop()
        self._running = False

    def statistics(self) -> dict:
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
                "metadata_sources": list(
                    self.metadata_bus.all_latest().keys()
                ),
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

        if metadata is None:
            return self.snapshot.capture(**kwargs)

        annotated = self.overlay.draw_metadata(frame, metadata)
        return self.snapshot.capture_frame(annotated, **kwargs)

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

    def enable_detection(self, name: str) -> None:
        self.detection.enable(name)

    def disable_detection(self, name: str) -> None:
        self.detection.disable(name)

    def detection_names(self) -> list[str]:
        return self.detection.names()

    def detection_status(self) -> dict[str, bool]:
        return {
            name: self.detection.is_enabled(name)
            for name in self.detection.names()
        }

    def enable_stream_overlay(self, source: str | None = None) -> None:
        self.streamer.enable_overlay(source)

    def disable_stream_overlay(self) -> None:
        self.streamer.disable_overlay()

    def stream_overlay_status(self) -> dict:
        return self.streamer.overlay_status()

    def enable_recording_overlay(self, source: str | None = None) -> None:
        self.recording.enable_overlay(source)

    def disable_recording_overlay(self) -> None:
        self.recording.disable_overlay()

    def recording_overlay_status(self) -> dict:
        return self.recording.overlay_status()

    def latest_metadata(self, source: str | None = None) -> Metadata | None:
        return self.metadata_bus.latest(source)

    def __enter__(self) -> "VisionService":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
