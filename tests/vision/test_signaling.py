from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp.test_utils import (
    TestClient,
    TestServer,
)

from betabox_robotics.vision.metadata import Metadata
from betabox_robotics.vision.recording import (
    RecordingData,
    RecordingError,
)
from betabox_robotics.vision.signaling import (
    INDEX_HTML,
    WebRTCSignalingServer,
    _validate_host,
    _validate_port,
    fail,
    ok,
    required_string,
    to_json,
)
from betabox_robotics.vision.snapshot import SnapshotData
from betabox_robotics.vision.stream import StreamError


@dataclass(frozen=True, slots=True)
class ExampleData:
    path: Path
    values: tuple[int, ...]


class SignalingValidationTests(unittest.TestCase):
    def test_validate_host(self) -> None:
        self.assertEqual(
            _validate_host(" 127.0.0.1 "),
            "127.0.0.1",
        )

    def test_validate_host_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "host must be a string",
        ):
            _validate_host(123)

    def test_validate_host_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "host cannot be empty",
        ):
            _validate_host(" ")

    def test_validate_port(self) -> None:
        self.assertEqual(
            _validate_port(8080),
            8080,
        )

    def test_validate_port_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            True,
            8080.0,
            "8080",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "port must be an integer",
                ),
            ):
                _validate_port(value)

    def test_validate_port_rejects_out_of_range_value(
        self,
    ) -> None:
        for value in (
            0,
            -1,
            65536,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "port must be between 1 and 65535",
                ),
            ):
                _validate_port(value)

    def test_required_string(self) -> None:
        self.assertEqual(
            required_string(
                {
                    "name": " color ",
                },
                "name",
            ),
            "color",
        )

    def test_required_string_rejects_missing_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name is required",
        ):
            required_string(
                {},
                "name",
            )

    def test_required_string_rejects_invalid_value(
        self,
    ) -> None:
        for value in (
            None,
            123,
            " ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "name is required",
                ),
            ):
                required_string(
                    {
                        "name": value,
                    },
                    "name",
                )


class SignalingSerializationTests(unittest.TestCase):
    def test_to_json_handles_dataclass(self) -> None:
        result = to_json(
            ExampleData(
                path=Path("example.txt"),
                values=(
                    1,
                    2,
                ),
            )
        )

        self.assertEqual(
            result,
            {
                "path": "example.txt",
                "values": [
                    1,
                    2,
                ],
            },
        )

    def test_to_json_handles_nested_values(self) -> None:
        result = to_json(
            {
                1: {
                    "paths": {
                        Path("first"),
                        Path("second"),
                    },
                },
            }
        )

        self.assertIn(
            "1",
            result,
        )
        self.assertEqual(
            set(result["1"]["paths"]),
            {
                "first",
                "second",
            },
        )

    def test_to_json_preserves_none(self) -> None:
        self.assertIsNone(to_json(None))

    def test_ok_response(self) -> None:
        response = ok(
            {
                "value": 1,
            }
        )

        self.assertEqual(
            response.status,
            200,
        )

    def test_fail_response(self) -> None:
        response = fail(
            "bad request",
            status=422,
        )

        self.assertEqual(
            response.status,
            422,
        )


class SignalingServerConstructionTests(unittest.TestCase):
    def test_requires_streamer(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "vision must provide a streamer",
        ):
            WebRTCSignalingServer(
                object(),  # type: ignore[arg-type]
            )

    def test_configuration(self) -> None:
        vision = MagicMock()
        vision.streamer = MagicMock()

        server = WebRTCSignalingServer(
            vision,
            host=" 127.0.0.1 ",
            port=9000,
        )

        self.assertIs(
            server.vision,
            vision,
        )
        self.assertIs(
            server.streamer,
            vision.streamer,
        )
        self.assertEqual(
            server.host,
            "127.0.0.1",
        )
        self.assertEqual(
            server.port,
            9000,
        )
        self.assertEqual(
            len(server.app.middlewares),
            1,
        )

    def test_registers_routes(self) -> None:
        vision = MagicMock()
        vision.streamer = MagicMock()

        server = WebRTCSignalingServer(vision)

        routes = {
            (
                route.method,
                route.resource.canonical,
            )
            for route in server.app.router.routes()
        }

        expected = {
            (
                "GET",
                "/",
            ),
            (
                "POST",
                "/offer",
            ),
            (
                "GET",
                "/stats",
            ),
            (
                "POST",
                "/snapshot",
            ),
            (
                "POST",
                "/recording/start",
            ),
            (
                "POST",
                "/recording/stop",
            ),
            (
                "GET",
                "/metadata",
            ),
            (
                "GET",
                "/detection",
            ),
            (
                "POST",
                "/detection/enable",
            ),
            (
                "POST",
                "/detection/disable",
            ),
            (
                "POST",
                "/detection/color/enable",
            ),
            (
                "POST",
                "/stream/overlay/enable",
            ),
            (
                "POST",
                "/stream/overlay/disable",
            ),
        }

        self.assertTrue(expected.issubset(routes))


class SignalingHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.vision = MagicMock()
        self.streamer = MagicMock()

        self.streamer.offer = AsyncMock()
        self.streamer.close_peers = AsyncMock()

        self.vision.streamer = self.streamer
        self.vision.statistics.return_value = {
            "running": True,
        }
        self.vision.detection_names.return_value = [
            "color",
            "face",
            "objects",
        ]
        self.vision.detection_status.return_value = {
            "color": True,
            "face": False,
            "objects": False,
        }
        self.vision.stream_overlay_status.return_value = {
            "enabled": False,
            "source": None,
        }

        self.signaling = WebRTCSignalingServer(
            self.vision,
            host="127.0.0.1",
            port=8080,
        )

        self.test_server = TestServer(self.signaling.app)
        self.client = TestClient(self.test_server)

        await self.client.start_server()

    async def asyncTearDown(self) -> None:
        await self.client.close()

    async def test_index(self) -> None:
        response = await self.client.get("/")

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            response.content_type,
            "text/html",
        )

        body = await response.text()

        self.assertIn(
            "Betabox Vision",
            body,
        )
        self.assertEqual(
            body,
            INDEX_HTML,
        )

    async def test_offer(self) -> None:
        self.streamer.offer.return_value = {
            "sdp": "answer-sdp",
            "type": "answer",
        }

        response = await self.client.post(
            "/offer",
            json={
                "sdp": " offer-sdp ",
                "type": " OFFER ",
            },
        )

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            await response.json(),
            {
                "sdp": "answer-sdp",
                "type": "answer",
            },
        )
        self.streamer.offer.assert_awaited_once_with(
            sdp="offer-sdp",
            offer_type="OFFER",
        )

    async def test_offer_rejects_invalid_json(
        self,
    ) -> None:
        response = await self.client.post(
            "/offer",
            data="{invalid",
            headers={
                "Content-Type": ("application/json"),
            },
        )

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            await response.json(),
            {
                "success": False,
                "error": ("request body must contain valid JSON"),
            },
        )

    async def test_offer_rejects_non_object_json(
        self,
    ) -> None:
        response = await self.client.post(
            "/offer",
            json=[
                "not",
                "an",
                "object",
            ],
        )

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "request JSON must be an object",
        )

    async def test_offer_rejects_missing_sdp(
        self,
    ) -> None:
        response = await self.client.post(
            "/offer",
            json={
                "type": "offer",
            },
        )

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "sdp is required",
        )

    async def test_offer_handles_stream_error(
        self,
    ) -> None:
        self.streamer.offer.side_effect = StreamError("negotiation failed")

        response = await self.client.post(
            "/offer",
            json={
                "sdp": "offer-sdp",
                "type": "offer",
            },
        )

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "negotiation failed",
        )

    async def test_stats(self) -> None:
        response = await self.client.get("/stats")

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "running": True,
                },
            },
        )
        self.vision.statistics.assert_called_once_with()

    async def test_snapshot_png(self) -> None:
        self.vision.capture_snapshot_data.return_value = SnapshotData(
            data=b"png-data",
            timestamp=123.5,
            format="png",
        )

        response = await self.client.post(
            "/snapshot?overlay=true&source=color&format=png"
        )

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            response.content_type,
            "image/png",
        )
        self.assertEqual(
            await response.read(),
            b"png-data",
        )
        self.assertEqual(
            response.headers["X-Betabox-Timestamp"],
            "123.5",
        )
        self.assertEqual(
            response.headers["X-Betabox-Format"],
            "png",
        )
        self.vision.capture_snapshot_data.assert_called_once_with(
            overlay=True,
            source="color",
            image_format="png",
        )

    async def test_snapshot_defaults_to_jpeg(
        self,
    ) -> None:
        self.vision.capture_snapshot_data.return_value = SnapshotData(
            data=b"jpeg-data",
            timestamp=10.0,
            format="jpg",
        )

        response = await self.client.post("/snapshot")

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            response.content_type,
            "image/jpeg",
        )
        self.vision.capture_snapshot_data.assert_called_once_with(
            overlay=False,
            source=None,
            image_format="jpg",
        )

    async def test_snapshot_rejects_invalid_boolean(
        self,
    ) -> None:
        response = await self.client.post("/snapshot?overlay=maybe")

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "overlay must be a boolean",
        )

    async def test_snapshot_rejects_invalid_format(
        self,
    ) -> None:
        response = await self.client.post("/snapshot?format=gif")

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "unsupported snapshot format: gif",
        )

    async def test_recording_start(self) -> None:
        response = await self.client.post(
            "/recording/start?filename=lesson.mp4&overlay=yes&source=face"
        )

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "recording": True,
                },
            },
        )
        self.vision.start_recording.assert_called_once_with(
            filename="lesson.mp4",
            overlay=True,
            source="face",
        )

    async def test_recording_start_handles_error(
        self,
    ) -> None:
        self.vision.start_recording.side_effect = RecordingError("recording failed")

        response = await self.client.post("/recording/start")

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "recording failed",
        )

    async def test_recording_stop(self) -> None:
        self.vision.stop_recording_data.return_value = RecordingData(
            data=b"video-data",
            format="mp4",
            start_timestamp=10.0,
            end_timestamp=12.0,
            frame_count=40,
            fps=20.0,
        )

        response = await self.client.post("/recording/stop")

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            response.content_type,
            "video/mp4",
        )
        self.assertEqual(
            await response.read(),
            b"video-data",
        )
        self.assertEqual(
            response.headers["X-Betabox-Format"],
            "mp4",
        )
        self.assertEqual(
            response.headers["X-Betabox-Start-Timestamp"],
            "10.0",
        )
        self.assertEqual(
            response.headers["X-Betabox-End-Timestamp"],
            "12.0",
        )
        self.assertEqual(
            response.headers["X-Betabox-Frame-Count"],
            "40",
        )
        self.assertEqual(
            response.headers["X-Betabox-FPS"],
            "20.0",
        )

    async def test_metadata(self) -> None:
        metadata = Metadata.create(
            "color",
            timestamp=123.5,
            data={
                "count": 1,
            },
        )
        self.vision.latest_metadata.return_value = metadata

        response = await self.client.get("/metadata?source=color")

        self.assertEqual(
            response.status,
            200,
        )

        body = await response.json()

        self.assertTrue(body["success"])
        self.assertEqual(
            body["data"]["source"],
            "color",
        )
        self.assertEqual(
            body["data"]["timestamp"],
            123.5,
        )
        self.vision.latest_metadata.assert_called_once_with("color")

    async def test_metadata_without_result(
        self,
    ) -> None:
        self.vision.latest_metadata.return_value = None

        response = await self.client.get("/metadata")

        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {},
            },
        )

    async def test_detection_status(self) -> None:
        response = await self.client.get("/detection")

        self.assertEqual(
            response.status,
            200,
        )
        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "detectors": [
                        "color",
                        "face",
                        "objects",
                    ],
                    "enabled": {
                        "color": True,
                        "face": False,
                        "objects": False,
                    },
                },
            },
        )

    async def test_detection_enable(self) -> None:
        response = await self.client.post(
            "/detection/enable",
            json={
                "name": " face ",
            },
        )

        self.assertEqual(
            response.status,
            200,
        )
        self.vision.enable_detection.assert_called_once_with("face")

        body = await response.json()

        self.assertEqual(
            body["data"]["enabled"],
            "face",
        )

    async def test_detection_enable_requires_name(
        self,
    ) -> None:
        response = await self.client.post(
            "/detection/enable",
            json={},
        )

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "name is required",
        )

    async def test_detection_disable(self) -> None:
        response = await self.client.post(
            "/detection/disable",
            json={
                "name": "color",
            },
        )

        self.assertEqual(
            response.status,
            200,
        )
        self.vision.disable_detection.assert_called_once_with("color")

        body = await response.json()

        self.assertEqual(
            body["data"]["disabled"],
            "color",
        )

    async def test_color_detection_enable(self) -> None:
        custom_ranges = {
            "team_marker": [
                [
                    [
                        10,
                        100,
                        100,
                    ],
                    [
                        20,
                        255,
                        255,
                    ],
                ],
            ],
        }

        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": [
                    "red",
                    "team_marker",
                ],
                "custom_ranges": (custom_ranges),
                "min_area": 25,
            },
        )

        self.assertEqual(
            response.status,
            200,
        )
        self.vision.enable_color_detection.assert_called_once_with(
            [
                "red",
                "team_marker",
            ],
            custom_ranges=custom_ranges,
            min_area=25,
        )

        body = await response.json()

        self.assertEqual(
            body["data"]["enabled"],
            "color",
        )

    async def test_color_detection_error_uses_middleware(
        self,
    ) -> None:
        self.vision.enable_color_detection.side_effect = ValueError(
            "unsupported color(s): invisible"
        )

        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": "invisible",
            },
        )

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "unsupported color(s): invisible",
        )

    async def test_stream_overlay_enable(self) -> None:
        self.vision.stream_overlay_status.return_value = {
            "enabled": True,
            "source": "color",
        }

        response = await self.client.post(
            "/stream/overlay/enable",
            json={
                "source": "color",
            },
        )

        self.assertEqual(
            response.status,
            200,
        )
        self.vision.enable_stream_overlay.assert_called_once_with("color")
        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "enabled": True,
                    "source": "color",
                },
            },
        )

    async def test_stream_overlay_enable_rejects_invalid_source(
        self,
    ) -> None:
        response = await self.client.post(
            "/stream/overlay/enable",
            json={
                "source": 123,
            },
        )

        self.assertEqual(
            response.status,
            400,
        )
        self.assertEqual(
            (await response.json())["error"],
            "source must be a string",
        )

    async def test_stream_overlay_disable(
        self,
    ) -> None:
        self.vision.stream_overlay_status.return_value = {
            "enabled": False,
            "source": None,
        }

        response = await self.client.post("/stream/overlay/disable")

        self.assertEqual(
            response.status,
            200,
        )
        self.vision.disable_stream_overlay.assert_called_once_with()
        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "enabled": False,
                    "source": None,
                },
            },
        )

    async def test_shutdown_closes_peers(self) -> None:
        await self.signaling.on_shutdown(self.signaling.app)

        self.streamer.close_peers.assert_awaited_once_with()


class SignalingRunTests(unittest.TestCase):
    def test_run(self) -> None:
        vision = MagicMock()
        vision.streamer = MagicMock()

        server = WebRTCSignalingServer(
            vision,
            host="127.0.0.1",
            port=9000,
        )

        with patch("betabox_robotics.vision.signaling.web.run_app") as run_app:
            server.run(handle_signals=False)

        run_app.assert_called_once_with(
            server.app,
            host="127.0.0.1",
            port=9000,
            handle_signals=False,
        )


if __name__ == "__main__":
    unittest.main()
