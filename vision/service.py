from __future__ import annotations

from dataclasses import dataclass

from betabox_robotics.vision.frame_source import FrameSource
from betabox_robotics.vision.signaling import WebRTCSignalingServer
from betabox_robotics.vision.webrtc import WebRTCStreamer


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

    def __init__(self, config: VisionServiceConfig | None = None) -> None:
        self.config = config or VisionServiceConfig()

        self.frame_source = FrameSource(fps=self.config.fps)
        self.streamer = WebRTCStreamer(fps=self.config.fps)
        self.server = WebRTCSignalingServer(
            self.streamer,
            host=self.config.host,
            port=self.config.port,
        )

        self.frame_source.register_consumer(self.streamer)
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
        self.frame_source.unregister_consumer(self.streamer)
        self.frame_source.stop()
        self._running = False

    def statistics(self) -> dict:
        return {
            "running": self._running,
            "frame_source_running": self.frame_source.is_running(),
            "frame_source_consumers": self.frame_source.consumer_count(),
            "streamer": self.streamer.statistics(),
            "host": self.config.host,
            "port": self.config.port,
            "fps": self.config.fps,
        }

    def close(self) -> None:
        self.stop()

    def __enter__(self) -> "VisionService":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
