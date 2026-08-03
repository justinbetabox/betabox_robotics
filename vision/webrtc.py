from __future__ import annotations

import asyncio
import fractions
import threading
from typing import Any

import numpy as np
from aiortc import (
    MediaStreamTrack,
    RTCPeerConnection,
    RTCSessionDescription,
)
from av.video.frame import VideoFrame

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer
from betabox_robotics.vision.stream import Streamer


class VisionVideoTrack(MediaStreamTrack):
    """
    WebRTC video track backed by the latest frame received by WebRTCStreamer.

    Betabox Vision frames use RGB channel order, matching PyAV's ``rgb24``
    ndarray format.
    """

    kind = "video"

    def __init__(
        self,
        streamer: WebRTCStreamer,
        fps: float = 20.0,
    ) -> None:
        super().__init__()

        if fps <= 0:
            raise ValueError("fps must be greater than zero")

        self.streamer = streamer
        self.fps = float(fps)

        self._timestamp = 0
        self._time_base = fractions.Fraction(1, 90_000)
        self._timestamp_step = int(90_000 / self.fps)

    async def recv(self) -> VideoFrame:
        await asyncio.sleep(1.0 / self.fps)

        frame = self.streamer.rendered_frame()

        if frame is None:
            image = np.zeros(
                (480, 640, 3),
                dtype=np.uint8,
            )
        else:
            # Copy so PyAV does not retain a buffer that another component
            # might later modify.
            image = frame.image.copy()

        video_frame = VideoFrame.from_ndarray(
            image,
            format="rgb24",
        )

        self._timestamp += self._timestamp_step
        video_frame.pts = self._timestamp
        video_frame.time_base = self._time_base

        return video_frame


class WebRTCStreamer(Streamer):
    """
    WebRTC streaming implementation.

    Receives RGB frames from FrameSource and serves them to WebRTC clients.
    The streamer retains only the latest frame, so a slow client cannot cause
    an unbounded frame backlog.
    """

    def __init__(
        self,
        *,
        fps: float = 20.0,
        metadata_bus: MetadataBus | None = None,
        overlay: OverlayRenderer | None = None,
    ) -> None:
        if fps <= 0:
            raise ValueError("fps must be greater than zero")

        self.fps = float(fps)
        self.metadata_bus = metadata_bus
        self.overlay = overlay or OverlayRenderer()

        self._running = False
        self._latest_frame: Frame | None = None
        self._frames_received = 0

        self._overlay_enabled = False
        self._overlay_source: str | None = None

        self._state_lock = threading.Lock()

        self._peer_connections: set[RTCPeerConnection] = set()
        self._peer_lock = threading.Lock()

    def start(self) -> None:
        with self._state_lock:
            if self._running:
                return

            self._latest_frame = None
            self._frames_received = 0
            self._running = True

    def stop(self) -> None:
        """
        Stop accepting and retaining frames.

        Peer connections are closed asynchronously through ``close_peers()``,
        normally by the signaling server's shutdown hook.
        """
        with self._state_lock:
            self._running = False
            self._latest_frame = None

    def on_frame(self, frame: Frame) -> None:
        with self._state_lock:
            if not self._running:
                return

            self._latest_frame = frame
            self._frames_received += 1

    def latest_frame(self) -> Frame | None:
        with self._state_lock:
            return self._latest_frame

    async def offer(
        self,
        sdp: str,
        type: str,
    ) -> dict[str, str]:
        """
        Handle a browser WebRTC offer and return its negotiated answer.

        A peer that fails during negotiation is closed and removed before the
        original exception is propagated.
        """
        pc = RTCPeerConnection()

        with self._peer_lock:
            self._peer_connections.add(pc)

        try:

            @pc.on("connectionstatechange")
            async def on_connectionstatechange() -> None:
                if pc.connectionState in (
                    "failed",
                    "disconnected",
                ):
                    await pc.close()

                if pc.connectionState == "closed":
                    with self._peer_lock:
                        self._peer_connections.discard(pc)

            pc.addTrack(
                VisionVideoTrack(
                    self,
                    fps=self.fps,
                )
            )

            remote_description = RTCSessionDescription(
                sdp=sdp,
                type=type,
            )

            await pc.setRemoteDescription(remote_description)

            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            local_description = pc.localDescription

            if local_description is None:
                raise RuntimeError("WebRTC peer did not produce a local description")

            return {
                "sdp": local_description.sdp,
                "type": local_description.type,
            }

        except Exception:
            with self._peer_lock:
                self._peer_connections.discard(pc)

            await pc.close()
            raise

    async def close_peers(self) -> None:
        with self._peer_lock:
            peers = tuple(self._peer_connections)

        if not peers:
            return

        await asyncio.gather(
            *(pc.close() for pc in peers),
            return_exceptions=True,
        )

        with self._peer_lock:
            self._peer_connections.difference_update(peers)

    def enable_overlay(
        self,
        source: str | None = None,
    ) -> None:
        with self._state_lock:
            self._overlay_enabled = True
            self._overlay_source = source

    def disable_overlay(self) -> None:
        with self._state_lock:
            self._overlay_enabled = False
            self._overlay_source = None

    def overlay_status(self) -> dict[str, bool | str | None]:
        with self._state_lock:
            return {
                "enabled": self._overlay_enabled,
                "source": self._overlay_source,
            }

    def rendered_frame(self) -> Frame | None:
        with self._state_lock:
            frame = self._latest_frame
            overlay_enabled = self._overlay_enabled
            overlay_source = self._overlay_source

        if frame is None:
            return None

        if not overlay_enabled or self.metadata_bus is None:
            return frame

        metadata = self.metadata_bus.latest(overlay_source)

        if metadata is None:
            return frame

        return self.overlay.draw_metadata(
            frame,
            metadata,
        )

    def clients(self) -> int:
        with self._peer_lock:
            return len(self._peer_connections)

    def statistics(self) -> dict[str, Any]:
        with self._state_lock:
            running = self._running
            frames_received = self._frames_received
            has_frame = self._latest_frame is not None
            overlay_status = {
                "enabled": self._overlay_enabled,
                "source": self._overlay_source,
            }

        return {
            "running": running,
            "clients": self.clients(),
            "overlay": overlay_status,
            "frames_received": frames_received,
            "has_frame": has_frame,
        }
