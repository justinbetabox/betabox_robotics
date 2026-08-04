from __future__ import annotations

import fractions
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np
from av.video.frame import VideoFrame

from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import (
    OverlayError,
    OverlayRenderer,
)
from betabox_robotics.vision.stream import StreamError
from betabox_robotics.vision.webrtc import (
    VisionVideoTrack,
    WebRTCStreamer,
    _validate_fps,
)


def create_test_frame(
    *,
    width: int = 40,
    height: int = 30,
    timestamp: float = 123.5,
) -> Frame:
    return Frame.create(
        np.zeros(
            (height, width, 3),
            dtype=np.uint8,
        ),
        timestamp=timestamp,
    )


class FakePeerConnection:
    def __init__(self) -> None:
        self.connectionState = "new"
        self.localDescription: SimpleNamespace | None = SimpleNamespace(
            sdp="answer-sdp",
            type="answer",
        )

        self.handlers: dict[str, object] = {}
        self.tracks: list[object] = []

        self.setRemoteDescription = AsyncMock()
        self.createAnswer = AsyncMock(
            return_value=SimpleNamespace(
                sdp="created-answer",
                type="answer",
            )
        )
        self.setLocalDescription = AsyncMock()
        self.close = AsyncMock()

    def on(
        self,
        event: str,
    ):
        def decorator(callback):
            self.handlers[event] = callback
            return callback

        return decorator

    def addTrack(
        self,
        track: object,
    ) -> None:
        self.tracks.append(track)


class WebRTCValidationTests(unittest.TestCase):
    def test_validate_fps(self) -> None:
        self.assertEqual(
            _validate_fps(20),
            20.0,
        )

    def test_validate_fps_rejects_invalid_type(self) -> None:
        for value in (
            True,
            "20",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "fps must be a number",
                ),
            ):
                _validate_fps(value)

    def test_validate_fps_rejects_non_finite_value(
        self,
    ) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be finite",
                ),
            ):
                _validate_fps(value)

    def test_validate_fps_rejects_non_positive_value(
        self,
    ) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be greater than zero",
                ),
            ):
                _validate_fps(value)


class WebRTCStreamerConfigurationTests(unittest.TestCase):
    def test_default_configuration(self) -> None:
        streamer = WebRTCStreamer()

        self.assertEqual(
            streamer.fps,
            20.0,
        )
        self.assertIsNone(streamer.metadata_bus)
        self.assertIsInstance(
            streamer.overlay,
            OverlayRenderer,
        )
        self.assertEqual(
            streamer.clients(),
            0,
        )
        self.assertEqual(
            streamer.overlay_status(),
            {
                "enabled": False,
                "source": None,
            },
        )

    def test_custom_configuration(self) -> None:
        metadata_bus = MetadataBus()
        overlay = OverlayRenderer()

        streamer = WebRTCStreamer(
            fps=15,
            metadata_bus=metadata_bus,
            overlay=overlay,
        )

        self.assertEqual(
            streamer.fps,
            15.0,
        )
        self.assertIs(
            streamer.metadata_bus,
            metadata_bus,
        )
        self.assertIs(
            streamer.overlay,
            overlay,
        )

    def test_rejects_invalid_metadata_bus(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "metadata_bus must be a MetadataBus",
        ):
            WebRTCStreamer(
                metadata_bus=object(),  # type: ignore[arg-type]
            )

    def test_rejects_invalid_overlay(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "overlay must be an OverlayRenderer",
        ):
            WebRTCStreamer(
                overlay=object(),  # type: ignore[arg-type]
            )


class WebRTCStreamerLifecycleTests(unittest.TestCase):
    def test_start(self) -> None:
        streamer = WebRTCStreamer()

        streamer.start()

        stats = streamer.statistics()

        self.assertTrue(stats["running"])
        self.assertEqual(
            stats["frames_received"],
            0,
        )
        self.assertFalse(stats["has_frame"])

    def test_start_is_idempotent(self) -> None:
        streamer = WebRTCStreamer()
        streamer.start()

        frame = create_test_frame()
        streamer.on_frame(frame)

        streamer.start()

        self.assertIs(
            streamer.latest_frame(),
            frame,
        )
        self.assertEqual(
            streamer.statistics()["frames_received"],
            1,
        )

    def test_stop(self) -> None:
        streamer = WebRTCStreamer()
        streamer.start()
        streamer.on_frame(create_test_frame())

        streamer.stop()

        stats = streamer.statistics()

        self.assertFalse(stats["running"])
        self.assertFalse(stats["has_frame"])
        self.assertIsNone(streamer.latest_frame())

    def test_stop_is_idempotent(self) -> None:
        streamer = WebRTCStreamer()

        streamer.stop()
        streamer.stop()

        self.assertFalse(streamer.statistics()["running"])


class WebRTCStreamerFrameTests(unittest.TestCase):
    def test_on_frame_requires_frame(self) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            TypeError,
            "frame must be a Frame instance",
        ):
            streamer.on_frame(
                object(),  # type: ignore[arg-type]
            )

    def test_on_frame_is_ignored_when_stopped(self) -> None:
        streamer = WebRTCStreamer()
        frame = create_test_frame()

        streamer.on_frame(frame)

        self.assertIsNone(streamer.latest_frame())
        self.assertEqual(
            streamer.statistics()["frames_received"],
            0,
        )

    def test_on_frame_retains_latest_frame(self) -> None:
        streamer = WebRTCStreamer()
        streamer.start()

        first = create_test_frame(
            timestamp=1.0,
        )
        second = create_test_frame(
            timestamp=2.0,
        )

        streamer.on_frame(first)
        streamer.on_frame(second)

        self.assertIs(
            streamer.latest_frame(),
            second,
        )
        self.assertEqual(
            streamer.statistics()["frames_received"],
            2,
        )

    def test_statistics_initial_state(self) -> None:
        streamer = WebRTCStreamer()

        self.assertEqual(
            streamer.statistics(),
            {
                "running": False,
                "clients": 0,
                "overlay": {
                    "enabled": False,
                    "source": None,
                },
                "frames_received": 0,
                "has_frame": False,
            },
        )


class WebRTCOverlayTests(unittest.TestCase):
    def test_enable_overlay(self) -> None:
        streamer = WebRTCStreamer()

        streamer.enable_overlay("color")

        self.assertEqual(
            streamer.overlay_status(),
            {
                "enabled": True,
                "source": "color",
            },
        )

    def test_enable_overlay_normalizes_source(self) -> None:
        streamer = WebRTCStreamer()

        streamer.enable_overlay("  color  ")

        self.assertEqual(
            streamer.overlay_status()["source"],
            "color",
        )

    def test_enable_overlay_rejects_invalid_source_type(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            TypeError,
            "source must be a string",
        ):
            streamer.enable_overlay(
                123,  # type: ignore[arg-type]
            )

    def test_enable_overlay_rejects_empty_source(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            ValueError,
            "source cannot be empty",
        ):
            streamer.enable_overlay(" ")

    def test_disable_overlay(self) -> None:
        streamer = WebRTCStreamer()
        streamer.enable_overlay("color")

        streamer.disable_overlay()

        self.assertEqual(
            streamer.overlay_status(),
            {
                "enabled": False,
                "source": None,
            },
        )

    def test_rendered_frame_returns_latest_frame_without_overlay(
        self,
    ) -> None:
        streamer = WebRTCStreamer()
        streamer.start()

        frame = create_test_frame()
        streamer.on_frame(frame)

        self.assertIs(
            streamer.rendered_frame(),
            frame,
        )

    def test_rendered_frame_returns_none_without_frame(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        self.assertIsNone(streamer.rendered_frame())

    def test_rendered_frame_returns_original_without_metadata(
        self,
    ) -> None:
        streamer = WebRTCStreamer(
            metadata_bus=MetadataBus(),
        )
        streamer.start()
        streamer.enable_overlay("color")

        frame = create_test_frame()
        streamer.on_frame(frame)

        self.assertIs(
            streamer.rendered_frame(),
            frame,
        )

    def test_rendered_frame_applies_overlay(self) -> None:
        metadata_bus = MetadataBus()
        metadata = Metadata.create("color")
        metadata_bus.publish(metadata)

        overlay = OverlayRenderer()
        streamer = WebRTCStreamer(
            metadata_bus=metadata_bus,
            overlay=overlay,
        )
        streamer.start()
        streamer.enable_overlay("color")

        frame = create_test_frame()
        rendered = create_test_frame(
            timestamp=frame.timestamp,
        )

        streamer.on_frame(frame)

        with patch.object(
            overlay,
            "draw_metadata",
            return_value=rendered,
        ) as draw_metadata:
            result = streamer.rendered_frame()

        self.assertIs(
            result,
            rendered,
        )
        draw_metadata.assert_called_once_with(
            frame,
            metadata,
        )

    def test_rendered_frame_ignores_overlay_failure(
        self,
    ) -> None:
        metadata_bus = MetadataBus()
        metadata_bus.publish(Metadata.create("color"))

        overlay = OverlayRenderer()
        streamer = WebRTCStreamer(
            metadata_bus=metadata_bus,
            overlay=overlay,
        )
        streamer.start()
        streamer.enable_overlay("color")

        frame = create_test_frame()
        streamer.on_frame(frame)

        with patch.object(
            overlay,
            "draw_metadata",
            side_effect=OverlayError("overlay failed"),
        ):
            result = streamer.rendered_frame()

        self.assertIs(
            result,
            frame,
        )


class VisionVideoTrackTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_streamer(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "streamer must be a WebRTCStreamer",
        ):
            VisionVideoTrack(
                object(),  # type: ignore[arg-type]
            )

    async def test_configuration(self) -> None:
        streamer = WebRTCStreamer()

        track = VisionVideoTrack(
            streamer,
            fps=20,
        )

        self.assertIs(
            track.streamer,
            streamer,
        )
        self.assertEqual(
            track.fps,
            20.0,
        )
        self.assertEqual(
            track._time_base,
            fractions.Fraction(
                1,
                90_000,
            ),
        )
        self.assertEqual(
            track._timestamp_step,
            4_500,
        )

    async def test_recv_returns_blank_frame_when_none_available(
        self,
    ) -> None:
        streamer = WebRTCStreamer()
        track = VisionVideoTrack(
            streamer,
            fps=20,
        )

        with patch(
            "betabox_robotics.vision.webrtc.asyncio.sleep",
            new=AsyncMock(),
        ):
            video_frame = await track.recv()

        self.assertIsInstance(
            video_frame,
            VideoFrame,
        )
        self.assertEqual(
            video_frame.width,
            640,
        )
        self.assertEqual(
            video_frame.height,
            480,
        )
        self.assertEqual(
            video_frame.pts,
            4_500,
        )
        self.assertEqual(
            video_frame.time_base,
            fractions.Fraction(
                1,
                90_000,
            ),
        )

    async def test_recv_uses_rendered_frame(self) -> None:
        streamer = WebRTCStreamer()
        frame = create_test_frame(
            width=50,
            height=25,
        )

        with patch.object(
            streamer,
            "rendered_frame",
            return_value=frame,
        ):
            track = VisionVideoTrack(
                streamer,
                fps=20,
            )

            with patch(
                "betabox_robotics.vision.webrtc.asyncio.sleep",
                new=AsyncMock(),
            ):
                video_frame = await track.recv()

        self.assertEqual(
            video_frame.width,
            50,
        )
        self.assertEqual(
            video_frame.height,
            25,
        )

    async def test_recv_does_not_modify_source_image(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        image = np.zeros(
            (20, 20, 3),
            dtype=np.uint8,
        )
        frame = Frame.create(image)
        original = image.copy()

        with patch.object(
            streamer,
            "rendered_frame",
            return_value=frame,
        ):
            track = VisionVideoTrack(streamer)

            with patch(
                "betabox_robotics.vision.webrtc.asyncio.sleep",
                new=AsyncMock(),
            ):
                await track.recv()

        np.testing.assert_array_equal(
            image,
            original,
        )

    async def test_recv_rejects_non_numpy_image(self) -> None:
        streamer = WebRTCStreamer()
        frame = Frame.create(object())

        with patch.object(
            streamer,
            "rendered_frame",
            return_value=frame,
        ):
            track = VisionVideoTrack(streamer)

            with (
                patch(
                    "betabox_robotics.vision.webrtc.asyncio.sleep",
                    new=AsyncMock(),
                ),
                self.assertRaisesRegex(
                    StreamError,
                    "stream frame image must be a NumPy array",
                ),
            ):
                await track.recv()

    async def test_recv_rejects_invalid_channel_count(
        self,
    ) -> None:
        streamer = WebRTCStreamer()
        frame = Frame.create(
            np.zeros(
                (20, 20),
                dtype=np.uint8,
            )
        )

        with patch.object(
            streamer,
            "rendered_frame",
            return_value=frame,
        ):
            track = VisionVideoTrack(streamer)

            with (
                patch(
                    "betabox_robotics.vision.webrtc.asyncio.sleep",
                    new=AsyncMock(),
                ),
                self.assertRaisesRegex(
                    StreamError,
                    "streaming requires a 3-channel image",
                ),
            ):
                await track.recv()

    async def test_recv_wraps_video_frame_failure(
        self,
    ) -> None:
        streamer = WebRTCStreamer()
        frame = create_test_frame()

        with (
            patch.object(
                streamer,
                "rendered_frame",
                return_value=frame,
            ),
            patch(
                "betabox_robotics.vision.webrtc.VideoFrame.from_ndarray",
                side_effect=ValueError("conversion failed"),
            ),
        ):
            track = VisionVideoTrack(streamer)

            with (
                patch(
                    "betabox_robotics.vision.webrtc.asyncio.sleep",
                    new=AsyncMock(),
                ),
                self.assertRaisesRegex(
                    StreamError,
                    "failed to create WebRTC video frame",
                ),
            ):
                await track.recv()

    async def test_recv_increments_timestamp(self) -> None:
        streamer = WebRTCStreamer()
        track = VisionVideoTrack(
            streamer,
            fps=20,
        )

        with patch(
            "betabox_robotics.vision.webrtc.asyncio.sleep",
            new=AsyncMock(),
        ):
            first = await track.recv()
            second = await track.recv()

        self.assertEqual(
            first.pts,
            4_500,
        )
        self.assertEqual(
            second.pts,
            9_000,
        )


class WebRTCOfferTests(unittest.IsolatedAsyncioTestCase):
    async def test_offer_rejects_invalid_sdp_type(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            TypeError,
            "sdp must be a string",
        ):
            await streamer.offer(
                123,  # type: ignore[arg-type]
                "offer",
            )

    async def test_offer_rejects_empty_sdp(self) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            ValueError,
            "sdp cannot be empty",
        ):
            await streamer.offer(
                " ",
                "offer",
            )

    async def test_offer_rejects_invalid_offer_type(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            TypeError,
            "offer_type must be a string",
        ):
            await streamer.offer(
                "offer-sdp",
                123,  # type: ignore[arg-type]
            )

    async def test_offer_rejects_empty_offer_type(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            ValueError,
            "offer_type cannot be empty",
        ):
            await streamer.offer(
                "offer-sdp",
                " ",
            )

    async def test_offer_returns_answer(self) -> None:
        streamer = WebRTCStreamer()
        peer = FakePeerConnection()

        with (
            patch(
                "betabox_robotics.vision.webrtc.RTCPeerConnection",
                return_value=peer,
            ),
            patch(
                "betabox_robotics.vision.webrtc.RTCSessionDescription",
                return_value=SimpleNamespace(
                    sdp="offer-sdp",
                    type="offer",
                ),
            ) as session_description,
        ):
            result = await streamer.offer(
                "  offer-sdp  ",
                " OFFER ",
            )

        self.assertEqual(
            result,
            {
                "sdp": "answer-sdp",
                "type": "answer",
            },
        )
        self.assertEqual(
            streamer.clients(),
            1,
        )
        self.assertEqual(
            len(peer.tracks),
            1,
        )
        self.assertIsInstance(
            peer.tracks[0],
            VisionVideoTrack,
        )

        session_description.assert_called_once_with(
            sdp="offer-sdp",
            type="offer",
        )
        peer.setRemoteDescription.assert_awaited_once()
        peer.createAnswer.assert_awaited_once_with()
        peer.setLocalDescription.assert_awaited_once()
        peer.close.assert_not_awaited()

    async def test_offer_cleans_up_failed_negotiation(
        self,
    ) -> None:
        streamer = WebRTCStreamer()
        peer = FakePeerConnection()
        peer.setRemoteDescription.side_effect = RuntimeError("negotiation failed")

        with (
            patch(
                "betabox_robotics.vision.webrtc.RTCPeerConnection",
                return_value=peer,
            ),
            patch(
                "betabox_robotics.vision.webrtc.RTCSessionDescription",
                return_value=SimpleNamespace(
                    sdp="offer-sdp",
                    type="offer",
                ),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "negotiation failed",
            ),
        ):
            await streamer.offer(
                "offer-sdp",
                "offer",
            )

        self.assertEqual(
            streamer.clients(),
            0,
        )
        peer.close.assert_awaited_once_with()

    async def test_offer_cleans_up_missing_local_description(
        self,
    ) -> None:
        streamer = WebRTCStreamer()
        peer = FakePeerConnection()
        peer.localDescription = None

        with (
            patch(
                "betabox_robotics.vision.webrtc.RTCPeerConnection",
                return_value=peer,
            ),
            patch(
                "betabox_robotics.vision.webrtc.RTCSessionDescription",
                return_value=SimpleNamespace(
                    sdp="offer-sdp",
                    type="offer",
                ),
            ),
            self.assertRaisesRegex(
                StreamError,
                "WebRTC peer did not produce a local description",
            ),
        ):
            await streamer.offer(
                "offer-sdp",
                "offer",
            )

        self.assertEqual(
            streamer.clients(),
            0,
        )
        peer.close.assert_awaited_once_with()

    async def test_connection_state_handler_closes_failed_peer(
        self,
    ) -> None:
        streamer = WebRTCStreamer()
        peer = FakePeerConnection()

        with (
            patch(
                "betabox_robotics.vision.webrtc.RTCPeerConnection",
                return_value=peer,
            ),
            patch(
                "betabox_robotics.vision.webrtc.RTCSessionDescription",
                return_value=SimpleNamespace(
                    sdp="offer-sdp",
                    type="offer",
                ),
            ),
        ):
            await streamer.offer(
                "offer-sdp",
                "offer",
            )

        handler = peer.handlers["connectionstatechange"]

        peer.connectionState = "failed"
        await handler()  # type: ignore[operator]

        peer.close.assert_awaited_once_with()

        peer.connectionState = "closed"
        await handler()  # type: ignore[operator]

        self.assertEqual(
            streamer.clients(),
            0,
        )


class WebRTCClosePeersTests(unittest.IsolatedAsyncioTestCase):
    async def test_close_peers_with_no_clients(self) -> None:
        streamer = WebRTCStreamer()

        await streamer.close_peers()

        self.assertEqual(
            streamer.clients(),
            0,
        )

    async def test_close_peers_closes_all_clients(self) -> None:
        streamer = WebRTCStreamer()

        first = FakePeerConnection()
        second = FakePeerConnection()

        with streamer._peer_lock:
            streamer._peer_connections.update(
                {
                    first,  # type: ignore[arg-type]
                    second,  # type: ignore[arg-type]
                }
            )

        await streamer.close_peers()

        first.close.assert_awaited_once_with()
        second.close.assert_awaited_once_with()
        self.assertEqual(
            streamer.clients(),
            0,
        )

    async def test_close_peers_continues_after_failure(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        first = FakePeerConnection()
        second = FakePeerConnection()

        first.close.side_effect = RuntimeError("close failed")

        with streamer._peer_lock:
            streamer._peer_connections.update(
                {
                    first,  # type: ignore[arg-type]
                    second,  # type: ignore[arg-type]
                }
            )

        await streamer.close_peers()

        first.close.assert_awaited_once_with()
        second.close.assert_awaited_once_with()
        self.assertEqual(
            streamer.clients(),
            0,
        )


if __name__ == "__main__":
    unittest.main()
