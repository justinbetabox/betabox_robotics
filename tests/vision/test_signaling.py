import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from betabox_robotics.vision.metadata import Detection, Metadata
from betabox_robotics.vision.recording import RecordingData
from betabox_robotics.vision.signaling import (
    INDEX_HTML,
    WebRTCSignalingServer,
    fail,
    json_object,
    ok,
    query_bool,
    required_string,
    to_json,
)
from betabox_robotics.vision.snapshot import SnapshotData


@dataclass(frozen=True)
class ExampleData:
    path: Path
    values: tuple[int, ...]


class SignalingHelperTests(unittest.IsolatedAsyncioTestCase):
    def test_to_json_none(self) -> None:
        self.assertIsNone(to_json(None))

    def test_to_json_path(self) -> None:
        self.assertEqual(
            to_json(Path("/tmp/example.jpg")),
            "/tmp/example.jpg",
        )

    def test_to_json_dataclass(self) -> None:
        value = ExampleData(
            path=Path("/tmp/example.jpg"),
            values=(1, 2, 3),
        )

        self.assertEqual(
            to_json(value),
            {
                "path": "/tmp/example.jpg",
                "values": [1, 2, 3],
            },
        )

    def test_to_json_nested_collections(self) -> None:
        value = {
            "paths": (
                Path("/tmp/one"),
                Path("/tmp/two"),
            ),
            "values": {1, 2},
        }

        result = to_json(value)

        self.assertEqual(
            result["paths"],
            [
                "/tmp/one",
                "/tmp/two",
            ],
        )
        self.assertEqual(
            set(result["values"]),
            {1, 2},
        )

    def test_ok_response(self) -> None:
        response = ok(
            {
                "path": Path("/tmp/example"),
            }
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "success": True,
                "data": {
                    "path": "/tmp/example",
                },
            },
        )

    def test_ok_response_without_data(self) -> None:
        response = ok()

        self.assertEqual(
            json.loads(response.body),
            {
                "success": True,
                "data": {},
            },
        )

    def test_fail_response(self) -> None:
        response = fail(
            "boom",
            status=409,
        )

        self.assertEqual(response.status, 409)
        self.assertEqual(
            json.loads(response.body),
            {
                "success": False,
                "error": "boom",
            },
        )

    def test_required_string_strips_whitespace(self) -> None:
        self.assertEqual(
            required_string(
                {"name": "  face  "},
                "name",
            ),
            "face",
        )

    def test_required_string_rejects_missing_value(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name is required",
        ):
            required_string({}, "name")

    def test_required_string_rejects_blank_value(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name is required",
        ):
            required_string(
                {"name": "   "},
                "name",
            )

    async def test_json_object_returns_dictionary(self) -> None:
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(
            return_value={
                "name": "face",
            }
        )

        result = await json_object(request)

        self.assertEqual(
            result,
            {
                "name": "face",
            },
        )

    async def test_json_object_wraps_invalid_json(self) -> None:
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(
            side_effect=json.JSONDecodeError(
                "bad JSON",
                "",
                0,
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "request body must contain valid JSON",
        ):
            await json_object(request)

    async def test_json_object_rejects_non_object(self) -> None:
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(
            return_value=[
                "face",
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "request JSON must be an object",
        ):
            await json_object(request)

    def test_query_bool_default(self) -> None:
        request = MagicMock(spec=web.Request)
        request.query = {}

        self.assertFalse(
            query_bool(
                request,
                "overlay",
            )
        )
        self.assertTrue(
            query_bool(
                request,
                "overlay",
                default=True,
            )
        )

    def test_query_bool_true_values(self) -> None:
        for value in (
            "1",
            "true",
            "TRUE",
            "yes",
            "YES",
        ):
            with self.subTest(value=value):
                request = MagicMock(spec=web.Request)
                request.query = {
                    "overlay": value,
                }

                self.assertTrue(
                    query_bool(
                        request,
                        "overlay",
                    )
                )

    def test_query_bool_false_values(self) -> None:
        for value in (
            "0",
            "false",
            "no",
            "anything",
        ):
            with self.subTest(value=value):
                request = MagicMock(spec=web.Request)
                request.query = {
                    "overlay": value,
                }

                self.assertFalse(
                    query_bool(
                        request,
                        "overlay",
                    )
                )


class WebRTCSignalingServerTests(AioHTTPTestCase):
    async def get_application(self) -> web.Application:
        self.vision = MagicMock()
        self.streamer = MagicMock()

        self.streamer.offer = AsyncMock()
        self.streamer.close_peers = AsyncMock()

        self.vision.streamer = self.streamer

        self.signaling_server = WebRTCSignalingServer(
            self.vision,
            host="127.0.0.1",
            port=8080,
        )

        return self.signaling_server.app

    async def test_routes_are_registered(self) -> None:
        routes = {
            (
                route.method,
                route.resource.canonical,
            )
            for route in self.server.app.router.routes()
        }

        expected = {
            ("GET", "/"),
            ("POST", "/offer"),
            ("GET", "/stats"),
            ("POST", "/snapshot"),
            ("POST", "/recording/start"),
            ("POST", "/recording/stop"),
            ("GET", "/metadata"),
            ("GET", "/detection"),
            ("POST", "/detection/enable"),
            ("POST", "/detection/color/enable"),
            ("POST", "/detection/disable"),
            ("POST", "/stream/overlay/enable"),
            ("POST", "/stream/overlay/disable"),
        }

        self.assertTrue(expected.issubset(routes))

    async def test_index_returns_html(self) -> None:
        response = await self.client.get("/")

        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.content_type,
            "text/html",
        )

        text = await response.text()

        self.assertEqual(text, INDEX_HTML)
        self.assertIn(
            "WebRTC answer applied",
            text,
        )
        self.assertIn(
            "if (!response.ok)",
            text,
        )

    async def test_offer_success(self) -> None:
        self.streamer.offer.return_value = {
            "sdp": "answer-sdp",
            "type": "answer",
        }

        response = await self.client.post(
            "/offer",
            json={
                "sdp": " offer-sdp ",
                "type": " offer ",
            },
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(
            await response.json(),
            {
                "sdp": "answer-sdp",
                "type": "answer",
            },
        )

        self.streamer.offer.assert_awaited_once_with(
            sdp="offer-sdp",
            type="offer",
        )

    async def test_offer_rejects_invalid_json(self) -> None:
        response = await self.client.post(
            "/offer",
            data="{",
            headers={
                "Content-Type": "application/json",
            },
        )

        self.assertEqual(response.status, 400)

        data = await response.json()

        self.assertFalse(data["success"])
        self.assertEqual(
            data["error"],
            "request body must contain valid JSON",
        )

    async def test_offer_rejects_missing_sdp(self) -> None:
        response = await self.client.post(
            "/offer",
            json={
                "type": "offer",
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            await response.json(),
            {
                "success": False,
                "error": "sdp is required",
            },
        )

    async def test_offer_wraps_streamer_failure(self) -> None:
        self.streamer.offer.side_effect = RuntimeError("negotiation failed")

        response = await self.client.post(
            "/offer",
            json={
                "sdp": "offer-sdp",
                "type": "offer",
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            await response.json(),
            {
                "success": False,
                "error": "negotiation failed",
            },
        )

    async def test_stats_returns_service_statistics(self) -> None:
        self.vision.statistics.return_value = {
            "running": True,
            "server": {
                "port": 8080,
            },
        }

        response = await self.client.get("/stats")

        self.assertEqual(response.status, 200)
        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "running": True,
                    "server": {
                        "port": 8080,
                    },
                },
            },
        )

    async def test_snapshot_returns_jpeg(self) -> None:
        snapshot = SnapshotData(
            data=b"jpeg-data",
            timestamp=123.5,
            format="jpg",
        )

        self.vision.capture_snapshot_data.return_value = snapshot

        response = await self.client.post(
            "/snapshot?overlay=true&source=face&format=jpg"
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.content_type,
            "image/jpeg",
        )
        self.assertEqual(
            await response.read(),
            b"jpeg-data",
        )
        self.assertEqual(
            response.headers["X-Betabox-Timestamp"],
            "123.5",
        )
        self.assertEqual(
            response.headers["X-Betabox-Format"],
            "jpg",
        )

        self.vision.capture_snapshot_data.assert_called_once_with(
            overlay=True,
            source="face",
            image_format="jpg",
        )

    async def test_snapshot_returns_png(self) -> None:
        self.vision.capture_snapshot_data.return_value = SnapshotData(
            data=b"png-data",
            timestamp=10.0,
            format="png",
        )

        response = await self.client.post("/snapshot?format=png")

        self.assertEqual(
            response.content_type,
            "image/png",
        )
        self.assertEqual(
            await response.read(),
            b"png-data",
        )

    async def test_snapshot_failure_returns_error(self) -> None:
        self.vision.capture_snapshot_data.side_effect = RuntimeError("snapshot failed")

        response = await self.client.post("/snapshot")

        self.assertEqual(response.status, 400)
        self.assertEqual(
            await response.json(),
            {
                "success": False,
                "error": "snapshot failed",
            },
        )

    async def test_recording_start(self) -> None:
        response = await self.client.post(
            "/recording/start?filename=lesson.mp4&overlay=yes&source=face"
        )

        self.assertEqual(response.status, 200)
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

    async def test_recording_start_failure(self) -> None:
        self.vision.start_recording.side_effect = RuntimeError(
            "recording already active"
        )

        response = await self.client.post("/recording/start")

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "recording already active",
        )

    async def test_recording_stop_returns_video(self) -> None:
        self.vision.stop_recording_data.return_value = RecordingData(
            data=b"video-data",
            format="mp4",
            start_timestamp=1.0,
            end_timestamp=2.5,
            frame_count=30,
            fps=20.0,
        )

        response = await self.client.post("/recording/stop")

        self.assertEqual(response.status, 200)
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
            "1.0",
        )
        self.assertEqual(
            response.headers["X-Betabox-End-Timestamp"],
            "2.5",
        )
        self.assertEqual(
            response.headers["X-Betabox-Frame-Count"],
            "30",
        )
        self.assertEqual(
            response.headers["X-Betabox-FPS"],
            "20.0",
        )

    async def test_metadata_returns_serialized_metadata(self) -> None:
        metadata = Metadata.create(
            "face",
            detections=(
                Detection(
                    label="face",
                    box=(1, 2, 3, 4),
                    center=(2, 4),
                ),
            ),
            data={
                "count": 1,
            },
        )

        self.vision.latest_metadata.return_value = metadata

        response = await self.client.get("/metadata?source=face")

        self.assertEqual(response.status, 200)

        data = await response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["data"]["source"],
            "face",
        )
        self.assertEqual(
            data["data"]["detections"][0]["box"],
            [1, 2, 3, 4],
        )

        self.vision.latest_metadata.assert_called_once_with("face")

    async def test_metadata_returns_empty_object_when_missing(self) -> None:
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
        self.vision.detection_names.return_value = [
            "color",
            "face",
        ]
        self.vision.detection_status.return_value = {
            "color": True,
            "face": False,
        }

        response = await self.client.get("/detection")

        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "detectors": [
                        "color",
                        "face",
                    ],
                    "enabled": {
                        "color": True,
                        "face": False,
                    },
                },
            },
        )

    async def test_detection_enable(self) -> None:
        self.vision.detection_status.return_value = {
            "face": True,
        }

        response = await self.client.post(
            "/detection/enable",
            json={
                "name": "  face  ",
            },
        )

        self.assertEqual(response.status, 200)
        self.vision.enable_detection.assert_called_once_with("face")

        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "enabled": "face",
                    "detectors": {
                        "face": True,
                    },
                },
            },
        )

    async def test_detection_enable_requires_name(self) -> None:
        response = await self.client.post(
            "/detection/enable",
            json={},
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "name is required",
        )

    async def test_detection_disable(self) -> None:
        self.vision.detection_status.return_value = {
            "face": False,
        }

        response = await self.client.post(
            "/detection/disable",
            json={
                "name": "face",
            },
        )

        self.assertEqual(response.status, 200)
        self.vision.disable_detection.assert_called_once_with("face")

        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "disabled": "face",
                    "detectors": {
                        "face": False,
                    },
                },
            },
        )

    async def test_color_detection_enable_with_multiple_colors(
        self,
    ) -> None:
        self.vision.detection_status.return_value = {
            "color": True,
            "face": False,
        }

        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": [
                    "red",
                    "green",
                    "blue",
                ],
                "min_area": 250,
            },
        )

        self.assertEqual(response.status, 200)

        self.vision.enable_color_detection.assert_called_once_with(
            [
                "red",
                "green",
                "blue",
            ],
            min_area=250.0,
        )

        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "enabled": "color",
                    "detectors": {
                        "color": True,
                        "face": False,
                    },
                },
            },
        )

    async def test_color_detection_enable_with_single_color(
        self,
    ) -> None:
        self.vision.detection_status.return_value = {
            "color": True,
        }

        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": "blue",
            },
        )

        self.assertEqual(response.status, 200)

        self.vision.enable_color_detection.assert_called_once_with(
            "blue",
            min_area=None,
        )

    async def test_color_detection_enable_with_empty_payload(
        self,
    ) -> None:
        self.vision.detection_status.return_value = {
            "color": True,
        }

        response = await self.client.post(
            "/detection/color/enable",
            json={},
        )

        self.assertEqual(response.status, 200)

        self.vision.enable_color_detection.assert_called_once_with(
            None,
            min_area=None,
        )

    async def test_color_detection_enable_rejects_invalid_colors_type(
        self,
    ) -> None:
        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": 123,
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "colors must be a string or list of strings",
        )

        self.vision.enable_color_detection.assert_not_called()

    async def test_color_detection_enable_rejects_non_string_list_item(
        self,
    ) -> None:
        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": [
                    "red",
                    123,
                ],
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "colors must contain only strings",
        )

    async def test_color_detection_enable_rejects_invalid_min_area(
        self,
    ) -> None:
        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": "red",
                "min_area": "large",
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "min_area must be a number",
        )

    async def test_color_detection_enable_rejects_negative_min_area(
        self,
    ) -> None:
        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": "red",
                "min_area": -1,
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "min_area cannot be negative",
        )

    async def test_color_detection_enable_wraps_service_failure(
        self,
    ) -> None:
        self.vision.enable_color_detection.side_effect = ValueError(
            "unsupported color(s): purple"
        )

        response = await self.client.post(
            "/detection/color/enable",
            json={
                "colors": "purple",
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "unsupported color(s): purple",
        )

    async def test_stream_overlay_enable(self) -> None:
        self.vision.stream_overlay_status.return_value = {
            "enabled": True,
            "source": "face",
        }

        response = await self.client.post(
            "/stream/overlay/enable",
            json={
                "source": "face",
            },
        )

        self.assertEqual(response.status, 200)
        self.vision.enable_stream_overlay.assert_called_once_with("face")

        self.assertEqual(
            await response.json(),
            {
                "success": True,
                "data": {
                    "enabled": True,
                    "source": "face",
                },
            },
        )

    async def test_stream_overlay_enable_rejects_non_string_source(
        self,
    ) -> None:
        response = await self.client.post(
            "/stream/overlay/enable",
            json={
                "source": 123,
            },
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(
            (await response.json())["error"],
            "source must be a string",
        )

    async def test_stream_overlay_disable(self) -> None:
        self.vision.stream_overlay_status.return_value = {
            "enabled": False,
            "source": None,
        }

        response = await self.client.post("/stream/overlay/disable")

        self.assertEqual(response.status, 200)
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
        await self.signaling_server.on_shutdown(self.signaling_server.app)

        self.streamer.close_peers.assert_awaited_once_with()

    async def test_run_uses_configured_server_values(self) -> None:
        with patch("betabox_robotics.vision.signaling.web.run_app") as run_app:
            self.signaling_server.run(handle_signals=False)

        run_app.assert_called_once_with(
            self.signaling_server.app,
            host="127.0.0.1",
            port=8080,
            handle_signals=False,
        )


if __name__ == "__main__":
    unittest.main()
