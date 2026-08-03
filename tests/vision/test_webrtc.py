import fractions
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from betabox_robotics.vision.frame import Frame
from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.metadata_bus import MetadataBus
from betabox_robotics.vision.overlay import OverlayRenderer
from betabox_robotics.vision.webrtc import (
    VisionVideoTrack,
    WebRTCStreamer,
)


class VisionVideoTrackTests(unittest.IsolatedAsyncioTestCase):
    def test_invalid_fps_raises(self) -> None:
        streamer = WebRTCStreamer()

        with self.assertRaisesRegex(
            ValueError,
            "fps must be greater than zero",
        ):
            VisionVideoTrack(streamer, fps=0)

    async def test_recv_returns_black_rgb_frame_when_no_frame_exists(
        self,
    ) -> None:
        streamer = MagicMock(spec=WebRTCStreamer)
        streamer.rendered_frame.return_value = None

        track = VisionVideoTrack(
            streamer,
            fps=20.0,
        )

        with patch(
            "betabox_robotics.vision.webrtc.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep:
            video_frame = await track.recv()

        sleep.assert_awaited_once_with(0.05)

        image = video_frame.to_ndarray(
            format="rgb24",
        )

        self.assertEqual(
            image.shape,
            (480, 640, 3),
        )
        self.assertTrue(np.all(image == 0))
        self.assertEqual(video_frame.pts, 4500)
        self.assertEqual(
            video_frame.time_base,
            fractions.Fraction(1, 90_000),
        )

    async def test_recv_converts_latest_rgb_frame(
        self,
    ) -> None:
        image = np.zeros(
            (20, 30, 3),
            dtype=np.uint8,
        )
        image[0, 0] = (255, 0, 0)

        frame = Frame.create(image)

        streamer = MagicMock(spec=WebRTCStreamer)
        streamer.rendered_frame.return_value = frame

        track = VisionVideoTrack(
            streamer,
            fps=20.0,
        )

        with patch(
            "betabox_robotics.vision.webrtc.asyncio.sleep",
            new=AsyncMock(),
        ):
            video_frame = await track.recv()

        result = video_frame.to_ndarray(
            format="rgb24",
        )

        np.testing.assert_array_equal(
            result,
            image,
        )

    async def test_recv_advances_timestamp(self) -> None:
        streamer = MagicMock(spec=WebRTCStreamer)
        streamer.rendered_frame.return_value = None

        track = VisionVideoTrack(
            streamer,
            fps=20.0,
        )

        with patch(
            "betabox_robotics.vision.webrtc.asyncio.sleep",
            new=AsyncMock(),
        ):
            first = await track.recv()
            second = await track.recv()

        self.assertEqual(first.pts, 4500)
        self.assertEqual(second.pts, 9000)


class WebRTCStreamerStateTests(unittest.TestCase):
    def test_invalid_fps_raises(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "fps must be greater than zero",
        ):
            WebRTCStreamer(fps=0)

    def test_initial_state(self) -> None:
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

    def test_start_resets_frame_state(self) -> None:
        streamer = WebRTCStreamer()
        frame = Frame.create(object())

        with streamer._state_lock:
            streamer._latest_frame = frame
            streamer._frames_received = 10

        streamer.start()

        self.assertTrue(streamer.statistics()["running"])
        self.assertIsNone(streamer.latest_frame())
        self.assertEqual(
            streamer.statistics()["frames_received"],
            0,
        )

    def test_start_is_idempotent(self) -> None:
        streamer = WebRTCStreamer()
        streamer.start()

        frame = Frame.create(object())
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

    def test_stop_clears_latest_frame(self) -> None:
        streamer = WebRTCStreamer()
        streamer.start()

        frame = Frame.create(object())
        streamer.on_frame(frame)

        streamer.stop()

        stats = streamer.statistics()

        self.assertFalse(stats["running"])
        self.assertFalse(stats["has_frame"])
        self.assertIsNone(streamer.latest_frame())

    def test_frame_is_ignored_while_stopped(self) -> None:
        streamer = WebRTCStreamer()
        frame = Frame.create(object())

        streamer.on_frame(frame)

        self.assertIsNone(streamer.latest_frame())
        self.assertEqual(
            streamer.statistics()["frames_received"],
            0,
        )

    def test_frame_is_retained_while_running(self) -> None:
        streamer = WebRTCStreamer()
        streamer.start()

        frame = Frame.create(object())
        streamer.on_frame(frame)

        self.assertIs(
            streamer.latest_frame(),
            frame,
        )
        self.assertEqual(
            streamer.statistics()["frames_received"],
            1,
        )

    def test_only_latest_frame_is_retained(self) -> None:
        streamer = WebRTCStreamer()
        streamer.start()

        first = Frame.create(object())
        second = Frame.create(object())

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


class WebRTCStreamerOverlayTests(unittest.TestCase):
    def test_enable_overlay(self) -> None:
        streamer = WebRTCStreamer()

        streamer.enable_overlay("face")

        self.assertEqual(
            streamer.overlay_status(),
            {
                "enabled": True,
                "source": "face",
            },
        )

    def test_disable_overlay(self) -> None:
        streamer = WebRTCStreamer()
        streamer.enable_overlay("face")

        streamer.disable_overlay()

        self.assertEqual(
            streamer.overlay_status(),
            {
                "enabled": False,
                "source": None,
            },
        )

    def test_rendered_frame_returns_original_when_overlay_disabled(
        self,
    ) -> None:
        bus = MagicMock(spec=MetadataBus)
        overlay = MagicMock(spec=OverlayRenderer)

        streamer = WebRTCStreamer(
            metadata_bus=bus,
            overlay=overlay,
        )
        streamer.start()

        frame = Frame.create(object())
        streamer.on_frame(frame)

        result = streamer.rendered_frame()

        self.assertIs(result, frame)
        bus.latest.assert_not_called()
        overlay.draw_metadata.assert_not_called()

    def test_rendered_frame_returns_original_without_metadata_bus(
        self,
    ) -> None:
        overlay = MagicMock(spec=OverlayRenderer)

        streamer = WebRTCStreamer(
            metadata_bus=None,
            overlay=overlay,
        )
        streamer.start()
        streamer.enable_overlay("face")

        frame = Frame.create(object())
        streamer.on_frame(frame)

        result = streamer.rendered_frame()

        self.assertIs(result, frame)
        overlay.draw_metadata.assert_not_called()

    def test_rendered_frame_returns_original_without_metadata(
        self,
    ) -> None:
        bus = MagicMock(spec=MetadataBus)
        overlay = MagicMock(spec=OverlayRenderer)
        bus.latest.return_value = None

        streamer = WebRTCStreamer(
            metadata_bus=bus,
            overlay=overlay,
        )
        streamer.start()
        streamer.enable_overlay("face")

        frame = Frame.create(object())
        streamer.on_frame(frame)

        result = streamer.rendered_frame()

        self.assertIs(result, frame)
        bus.latest.assert_called_once_with("face")
        overlay.draw_metadata.assert_not_called()

    def test_rendered_frame_draws_requested_overlay(
        self,
    ) -> None:
        bus = MagicMock(spec=MetadataBus)
        overlay = MagicMock(spec=OverlayRenderer)

        streamer = WebRTCStreamer(
            metadata_bus=bus,
            overlay=overlay,
        )
        streamer.start()
        streamer.enable_overlay("face")

        frame = Frame.create(object())
        annotated = Frame.create(object())
        metadata = Metadata(
            source="face",
            timestamp=frame.timestamp,
        )

        streamer.on_frame(frame)
        bus.latest.return_value = metadata
        overlay.draw_metadata.return_value = annotated

        result = streamer.rendered_frame()

        self.assertIs(result, annotated)
        bus.latest.assert_called_once_with("face")
        overlay.draw_metadata.assert_called_once_with(
            frame,
            metadata,
        )


class WebRTCStreamerPeerTests(unittest.IsolatedAsyncioTestCase):
    async def test_offer_returns_local_description(self) -> None:
        pc = MagicMock()
        pc.connectionState = "new"
        pc.setRemoteDescription = AsyncMock()
        pc.createAnswer = AsyncMock(return_value=MagicMock())
        pc.setLocalDescription = AsyncMock()
        pc.close = AsyncMock()

        local_description = MagicMock()
        local_description.sdp = "answer-sdp"
        local_description.type = "answer"
        pc.localDescription = local_description

        handlers = {}

        def register_handler(name):
            def decorator(callback):
                handlers[name] = callback
                return callback

            return decorator

        pc.on.side_effect = register_handler

        streamer = WebRTCStreamer()

        with (
            patch(
                "betabox_robotics.vision.webrtc.RTCPeerConnection",
                return_value=pc,
            ),
            patch(
                "betabox_robotics.vision.webrtc.RTCSessionDescription"
            ) as session_description,
        ):
            result = await streamer.offer(
                "offer-sdp",
                "offer",
            )

        self.assertEqual(
            result,
            {
                "sdp": "answer-sdp",
                "type": "answer",
            },
        )
        self.assertEqual(streamer.clients(), 1)
        pc.addTrack.assert_called_once()
        session_description.assert_called_once_with(
            sdp="offer-sdp",
            type="offer",
        )
        pc.setRemoteDescription.assert_awaited_once()
        pc.createAnswer.assert_awaited_once()
        pc.setLocalDescription.assert_awaited_once()

    async def test_failed_offer_closes_and_removes_peer(
        self,
    ) -> None:
        pc = MagicMock()
        pc.setRemoteDescription = AsyncMock(side_effect=RuntimeError("boom"))
        pc.close = AsyncMock()

        pc.on.side_effect = lambda name: lambda callback: callback

        streamer = WebRTCStreamer()

        with (
            patch(
                "betabox_robotics.vision.webrtc.RTCPeerConnection",
                return_value=pc,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "boom",
            ),
        ):
            await streamer.offer(
                "offer-sdp",
                "offer",
            )

        self.assertEqual(streamer.clients(), 0)
        pc.close.assert_awaited_once()

    async def test_closed_connection_is_removed(self) -> None:
        pc = MagicMock()
        pc.connectionState = "new"
        pc.setRemoteDescription = AsyncMock()
        pc.createAnswer = AsyncMock(return_value=MagicMock())
        pc.setLocalDescription = AsyncMock()
        pc.close = AsyncMock()

        local_description = MagicMock()
        local_description.sdp = "answer-sdp"
        local_description.type = "answer"
        pc.localDescription = local_description

        handlers = {}

        def register_handler(name):
            def decorator(callback):
                handlers[name] = callback
                return callback

            return decorator

        pc.on.side_effect = register_handler

        streamer = WebRTCStreamer()

        with patch(
            "betabox_robotics.vision.webrtc.RTCPeerConnection",
            return_value=pc,
        ):
            await streamer.offer(
                "offer-sdp",
                "offer",
            )

        self.assertEqual(streamer.clients(), 1)

        pc.connectionState = "closed"
        await handlers["connectionstatechange"]()

        self.assertEqual(streamer.clients(), 0)

    async def test_failed_connection_is_closed(self) -> None:
        pc = MagicMock()
        pc.connectionState = "new"
        pc.setRemoteDescription = AsyncMock()
        pc.createAnswer = AsyncMock(return_value=MagicMock())
        pc.setLocalDescription = AsyncMock()
        pc.close = AsyncMock()

        local_description = MagicMock()
        local_description.sdp = "answer-sdp"
        local_description.type = "answer"
        pc.localDescription = local_description

        handlers = {}

        def register_handler(name):
            def decorator(callback):
                handlers[name] = callback
                return callback

            return decorator

        pc.on.side_effect = register_handler

        streamer = WebRTCStreamer()

        with patch(
            "betabox_robotics.vision.webrtc.RTCPeerConnection",
            return_value=pc,
        ):
            await streamer.offer(
                "offer-sdp",
                "offer",
            )

        pc.connectionState = "failed"
        await handlers["connectionstatechange"]()

        pc.close.assert_awaited_once()

    async def test_close_peers_closes_all_connections(
        self,
    ) -> None:
        first = MagicMock()
        first.close = AsyncMock()

        second = MagicMock()
        second.close = AsyncMock()

        streamer = WebRTCStreamer()

        with streamer._peer_lock:
            streamer._peer_connections.update(
                {
                    first,
                    second,
                }
            )

        await streamer.close_peers()

        first.close.assert_awaited_once()
        second.close.assert_awaited_once()
        self.assertEqual(streamer.clients(), 0)

    async def test_close_peers_with_no_connections_is_noop(
        self,
    ) -> None:
        streamer = WebRTCStreamer()

        await streamer.close_peers()

        self.assertEqual(streamer.clients(), 0)


if __name__ == "__main__":
    unittest.main()
