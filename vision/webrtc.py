import asyncio
import fractions
import threading
from typing import Any, Dict, Optional, Set

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from av.video.frame import VideoFrame

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.stream import Streamer
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer


class VisionVideoTrack(MediaStreamTrack):
    """
    WebRTC video track backed by the latest frame received from FrameSource.
    """

    kind = "video"

    def __init__(self, streamer: "WebRTCStreamer", fps: float = 20.0) -> None:
        super().__init__()
        self.streamer = streamer
        self.fps = float(fps)
        self._timestamp = 0
        self._time_base = fractions.Fraction(1, 90000)

    async def recv(self):
        await asyncio.sleep(1.0 / self.fps)

        frame = self.streamer.rendered_frame()

        if frame is None:
            video_frame = VideoFrame(width=640, height=480, format="rgb24")
        else:
            video_frame = VideoFrame.from_ndarray(frame.image, format="rgb24")

        self._timestamp += int(90000 / self.fps)

        video_frame.pts = self._timestamp
        video_frame.time_base = self._time_base

        return video_frame


class WebRTCStreamer(Streamer):
    """
    WebRTC streaming implementation.

    Receives frames from FrameSource and serves them to WebRTC clients.
    """

    def __init__(
        self,
        *,
        fps: float = 20.0,
        metadata_bus: MetadataBus | None = None,
        overlay: OverlayRenderer | None = None,
    ) -> None:
        self.fps = float(fps)
        self.metadata_bus = metadata_bus
        self.overlay = overlay or OverlayRenderer()
        self.overlay_enabled = False
        self.overlay_source: str | None = None
        self._running = False
        self._latest_frame: Optional[Frame] = None
        self._frames_received = 0
        self._lock = threading.Lock()
        self._peer_connections: Set[RTCPeerConnection] = set()

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._latest_frame = None

    def on_frame(self, frame: Frame) -> None:
        if not self._running:
            return

        with self._lock:
            self._latest_frame = frame
            self._frames_received += 1

    def latest_frame(self) -> Optional[Frame]:
        with self._lock:
            return self._latest_frame

    async def offer(self, sdp: str, type: str) -> Dict[str, str]:
        """
        Handle a browser WebRTC offer and return an answer.
        """
        pc = RTCPeerConnection()
        self._peer_connections.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            if pc.connectionState in ("failed", "closed", "disconnected"):
                await pc.close()
                self._peer_connections.discard(pc)

        pc.addTrack(VisionVideoTrack(self, fps=self.fps))

        offer = RTCSessionDescription(sdp=sdp, type=type)
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        }

    def enable_overlay(self, source: str | None = None) -> None:
        self.overlay_enabled = True
        self.overlay_source = source

    def disable_overlay(self) -> None:
        self.overlay_enabled = False
        self.overlay_source = None

    def overlay_status(self) -> dict:
        return {
            "enabled": self.overlay_enabled,
            "source": self.overlay_source,
        }

    def rendered_frame(self) -> Frame | None:
        frame = self.latest_frame()

        if frame is None:
            return None

        if not self.overlay_enabled or self.metadata_bus is None:
            return frame

        metadata = self.metadata_bus.latest(self.overlay_source)

        if metadata is None:
            return frame

        return self.overlay.draw_metadata(frame, metadata)

    async def close_peers(self) -> None:
        pcs = list(self._peer_connections)

        for pc in pcs:
            await pc.close()

        self._peer_connections.clear()

    def clients(self) -> int:
        return len(self._peer_connections)

    def statistics(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "clients": self.clients(),
            "overlay": self.overlay_status(),
            "frames_received": self._frames_received,
            "has_frame": self.latest_frame() is not None,
        }
