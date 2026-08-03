from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib import error, request

from betabox_robotics.vision.client import (
    ClientCameraStatistics,
    ClientDetection,
    ClientDetectionStatistics,
    ClientDetectionStatus,
    ClientMetadata,
    ClientRecording,
    ClientRecordingStatus,
    ClientSnapshot,
    ClientStreamingStatistics,
    ClientStreamOverlayStatus,
    ClientVisionServerStatistics,
    ClientVisionStatistics,
    VisionClient,
    VisionClientError,
)


def mock_response(
    body: bytes,
    *,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    response = MagicMock()
    response.read.return_value = body
    response.headers = headers or {}
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def http_error(
    *,
    code: int = 400,
    body: bytes = b"",
) -> error.HTTPError:
    return error.HTTPError(
        url="http://127.0.0.1:8080/test",
        code=code,
        msg="error",
        hdrs=None,
        fp=io.BytesIO(body),
    )


class ClientModelTests(unittest.TestCase):
    def test_recording_duration(self) -> None:
        recording = ClientRecording(
            path=Path("/tmp/video.mp4"),
            start_timestamp=10.0,
            end_timestamp=12.5,
            frame_count=50,
            fps=20.0,
        )

        self.assertEqual(recording.duration, 2.5)

    def test_recording_duration_never_negative(self) -> None:
        recording = ClientRecording(
            path=Path("/tmp/video.mp4"),
            start_timestamp=12.0,
            end_timestamp=10.0,
            frame_count=0,
            fps=20.0,
        )

        self.assertEqual(recording.duration, 0.0)

    def test_detection_status_properties(self) -> None:
        status = ClientDetectionStatus(
            detectors={
                "color": True,
                "face": False,
                "object": True,
            },
        )

        self.assertEqual(
            status.enabled,
            ["color", "object"],
        )
        self.assertEqual(
            status.disabled,
            ["face"],
        )
        self.assertTrue(status.is_enabled("color"))
        self.assertFalse(status.is_enabled("face"))
        self.assertFalse(status.is_enabled("missing"))


class VisionClientConstructionTests(unittest.TestCase):
    def test_defaults(self) -> None:
        client = VisionClient()

        self.assertEqual(
            client.base_url,
            "http://127.0.0.1:8080",
        )
        self.assertEqual(client.timeout, 10.0)
        self.assertIsNone(client._recording_filename)

    def test_trailing_slash_is_removed(self) -> None:
        client = VisionClient(
            "http://example.test:8080/",
        )

        self.assertEqual(
            client.base_url,
            "http://example.test:8080",
        )

    def test_empty_base_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "base_url cannot be empty",
        ):
            VisionClient("")

    def test_invalid_timeout_is_rejected(self) -> None:
        for timeout in (0, -1):
            with (
                self.subTest(timeout=timeout),
                self.assertRaisesRegex(
                    VisionClientError,
                    "timeout must be greater than 0",
                ),
            ):
                VisionClient(timeout=timeout)

    def test_default_uses_vision_config(self) -> None:
        config = MagicMock()
        config.service_url = "http://robot.local:9000"
        config.request_timeout = 4.5

        client = VisionClient.default(config)

        self.assertEqual(
            client.base_url,
            "http://robot.local:9000",
        )
        self.assertEqual(client.timeout, 4.5)


class VisionClientPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_snapshot_format_defaults_to_jpg(self) -> None:
        self.assertEqual(
            self.client._snapshot_format(None),
            "jpg",
        )
        self.assertEqual(
            self.client._snapshot_format("photo"),
            "jpg",
        )

    def test_snapshot_format_accepts_jpeg_extensions(self) -> None:
        self.assertEqual(
            self.client._snapshot_format("photo.jpg"),
            "jpg",
        )
        self.assertEqual(
            self.client._snapshot_format("photo.JPEG"),
            "jpg",
        )

    def test_snapshot_format_accepts_png(self) -> None:
        self.assertEqual(
            self.client._snapshot_format("photo.PNG"),
            "png",
        )

    def test_snapshot_format_rejects_unknown_extension(self) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "snapshot filename must use",
        ):
            self.client._snapshot_format("photo.gif")

    def test_path_with_query_without_parameters(self) -> None:
        self.assertEqual(
            self.client._path_with_query(
                "/metadata",
                {
                    "source": None,
                },
            ),
            "/metadata",
        )

    def test_path_with_query_filters_none(self) -> None:
        result = self.client._path_with_query(
            "/snapshot",
            {
                "format": "jpg",
                "overlay": None,
                "source": "face",
            },
        )

        self.assertEqual(
            result,
            "/snapshot?format=jpg&source=face",
        )

    def test_path_with_query_encodes_values(self) -> None:
        result = self.client._path_with_query(
            "/metadata",
            {
                "source": "face detector",
            },
        )

        self.assertEqual(
            result,
            "/metadata?source=face+detector",
        )

    def test_media_output_path_creates_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "pictures"

            result = self.client._media_output_path(
                directory=directory,
                filename="photo.jpg",
                media_name="snapshot",
                extension="jpg",
            )

            self.assertTrue(directory.is_dir())
            self.assertEqual(
                result,
                directory / "photo.jpg",
            )

    def test_media_output_path_adds_extension(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)

            result = self.client._media_output_path(
                directory=directory,
                filename="photo",
                media_name="snapshot",
                extension="jpg",
            )

            self.assertEqual(
                result,
                directory / "photo.jpg",
            )

    def test_media_output_path_replaces_extension(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)

            result = self.client._media_output_path(
                directory=directory,
                filename="photo.jpeg",
                media_name="snapshot",
                extension="jpg",
            )

            self.assertEqual(
                result,
                directory / "photo.jpg",
            )

    def test_media_output_path_rejects_directory_components(self) -> None:
        with (
            TemporaryDirectory() as tmp,
            self.assertRaisesRegex(
                VisionClientError,
                "plain filename",
            ),
        ):
            self.client._media_output_path(
                directory=Path(tmp),
                filename="../photo.jpg",
                media_name="snapshot",
                extension="jpg",
            )

    def test_media_output_path_rejects_blank_filename(self) -> None:
        with (
            TemporaryDirectory() as tmp,
            self.assertRaisesRegex(
                VisionClientError,
                "plain filename",
            ),
        ):
            self.client._media_output_path(
                directory=Path(tmp),
                filename="   ",
                media_name="snapshot",
                extension="jpg",
            )

    def test_media_output_path_wraps_directory_error(self) -> None:
        directory = MagicMock(spec=Path)
        directory.mkdir.side_effect = OSError("permission denied")

        with self.assertRaisesRegex(
            VisionClientError,
            "failed to create media directory",
        ):
            self.client._media_output_path(
                directory=directory,
                filename="photo.jpg",
                media_name="snapshot",
                extension="jpg",
            )

    def test_save_media_file(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.bin"

            self.client._save_media_file(
                path,
                b"content",
                "snapshot",
            )

            self.assertEqual(
                path.read_bytes(),
                b"content",
            )

    def test_save_media_file_wraps_os_error(self) -> None:
        path = MagicMock(spec=Path)
        path.write_bytes.side_effect = OSError("permission denied")

        with self.assertRaisesRegex(
            VisionClientError,
            "failed to save snapshot",
        ):
            self.client._save_media_file(
                path,
                b"content",
                "snapshot",
            )


class VisionClientRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient(
            "http://robot.local:8080",
            timeout=3.0,
        )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_returns_success_payload(
        self,
        urlopen,
    ) -> None:
        urlopen.return_value = mock_response(
            json.dumps(
                {
                    "success": True,
                    "data": {
                        "running": True,
                    },
                }
            ).encode()
        )

        result = self.client._request(
            "GET",
            "/stats",
        )

        self.assertEqual(
            result,
            {
                "running": True,
            },
        )

        req = urlopen.call_args.args[0]

        self.assertIsInstance(req, request.Request)
        self.assertEqual(
            req.full_url,
            "http://robot.local:8080/stats",
        )
        self.assertEqual(req.method, "GET")
        self.assertEqual(
            urlopen.call_args.kwargs["timeout"],
            3.0,
        )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_posts_json(
        self,
        urlopen,
    ) -> None:
        urlopen.return_value = mock_response(b'{"success": true, "data": {}}')

        self.client._request(
            "POST",
            "/detection/enable",
            data={
                "name": "face",
            },
        )

        req = urlopen.call_args.args[0]

        self.assertEqual(req.method, "POST")
        self.assertEqual(
            json.loads(req.data),
            {
                "name": "face",
            },
        )
        self.assertEqual(
            req.headers["Content-type"],
            "application/json",
        )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_wraps_json_http_error(
        self,
        urlopen,
    ) -> None:
        urlopen.side_effect = http_error(
            code=400,
            body=b'{"error": "unknown detector"}',
        )

        with self.assertRaisesRegex(
            VisionClientError,
            "unknown detector",
        ):
            self.client._request(
                "POST",
                "/detection/enable",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_wraps_non_json_http_error(
        self,
        urlopen,
    ) -> None:
        urlopen.side_effect = http_error(
            code=500,
            body=b"server error",
        )

        with self.assertRaisesRegex(
            VisionClientError,
            "HTTP 500",
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_wraps_url_error(
        self,
        urlopen,
    ) -> None:
        urlopen.side_effect = error.URLError("connection refused")

        with self.assertRaisesRegex(
            VisionClientError,
            "Betabox Vision service is not available",
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_rejects_invalid_json(
        self,
        urlopen,
    ) -> None:
        urlopen.return_value = mock_response(b"not-json")

        with self.assertRaisesRegex(
            VisionClientError,
            "invalid Vision service response",
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_rejects_non_object_response(
        self,
        urlopen,
    ) -> None:
        urlopen.return_value = mock_response(b'["unexpected"]')

        with self.assertRaisesRegex(
            VisionClientError,
            "unexpected response",
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_rejects_unsuccessful_response(
        self,
        urlopen,
    ) -> None:
        urlopen.return_value = mock_response(b'{"success": false, "error": "boom"}')

        with self.assertRaisesRegex(
            VisionClientError,
            "boom",
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_rejects_non_object_data(
        self,
        urlopen,
    ) -> None:
        urlopen.return_value = mock_response(b'{"success": true, "data": []}')

        with self.assertRaisesRegex(
            VisionClientError,
            "invalid data",
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_bytes_returns_body_and_headers(
        self,
        urlopen,
    ) -> None:
        headers = {
            "X-Betabox-Format": "jpg",
        }
        urlopen.return_value = mock_response(
            b"image-data",
            headers=headers,
        )

        body, returned_headers = self.client._request_bytes(
            "POST",
            "/snapshot",
        )

        self.assertEqual(body, b"image-data")
        self.assertIs(returned_headers, headers)

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_bytes_wraps_http_error(
        self,
        urlopen,
    ) -> None:
        urlopen.side_effect = http_error(
            code=400,
            body=b'{"error": "snapshot failed"}',
        )

        with self.assertRaisesRegex(
            VisionClientError,
            "snapshot failed",
        ):
            self.client._request_bytes(
                "POST",
                "/snapshot",
            )

    @patch("betabox_robotics.vision.client.request.urlopen")
    def test_request_bytes_wraps_url_error(
        self,
        urlopen,
    ) -> None:
        urlopen.side_effect = error.URLError("connection refused")

        with self.assertRaisesRegex(
            VisionClientError,
            "Betabox Vision service is not available",
        ):
            self.client._request_bytes(
                "POST",
                "/snapshot",
            )


class VisionClientParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_parse_float(self) -> None:
        self.assertEqual(
            self.client._parse_float(
                "12.5",
                field="value",
            ),
            12.5,
        )

    def test_parse_float_wraps_invalid_value(self) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid camera FPS",
        ):
            self.client._parse_float(
                "bad",
                field="camera FPS",
            )

    def test_parse_int(self) -> None:
        self.assertEqual(
            self.client._parse_int(
                "12",
                field="value",
            ),
            12,
        )

    def test_parse_int_wraps_invalid_value(self) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid server port",
        ):
            self.client._parse_int(
                None,
                field="server port",
            )

    def test_parse_detection(self) -> None:
        result = self.client._parse_detection(
            {
                "label": "face",
                "confidence": "0.9",
                "box": [1, 2, 30, 40],
                "center": [16, 22],
                "data": {
                    "width": 30,
                },
            }
        )

        self.assertEqual(
            result,
            ClientDetection(
                label="face",
                confidence=0.9,
                box=(1, 2, 30, 40),
                center=(16, 22),
                data={
                    "width": 30,
                },
            ),
        )

    def test_parse_detection_allows_missing_optional_fields(
        self,
    ) -> None:
        result = self.client._parse_detection(
            {
                "label": "face",
            }
        )

        self.assertIsNone(result.confidence)
        self.assertIsNone(result.box)
        self.assertIsNone(result.center)
        self.assertEqual(result.data, {})

    def test_parse_detection_ignores_wrong_box_length(
        self,
    ) -> None:
        result = self.client._parse_detection(
            {
                "label": "face",
                "box": [1, 2],
            }
        )

        self.assertIsNone(result.box)

    def test_parse_detection_rejects_invalid_box_values(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid detection box",
        ):
            self.client._parse_detection(
                {
                    "box": [
                        1,
                        2,
                        "bad",
                        4,
                    ],
                }
            )

    def test_parse_detection_rejects_invalid_center_values(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid detection center",
        ):
            self.client._parse_detection(
                {
                    "center": [
                        1,
                        "bad",
                    ],
                }
            )

    def test_parse_detection_rejects_invalid_confidence(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid detection confidence",
        ):
            self.client._parse_detection(
                {
                    "confidence": "bad",
                }
            )

    def test_parse_metadata(self) -> None:
        result = self.client._parse_metadata(
            {
                "source": "face",
                "timestamp": "12.5",
                "detections": [
                    {
                        "label": "face",
                        "box": [1, 2, 3, 4],
                    },
                    "ignored",
                ],
                "data": {
                    "count": 1,
                },
            }
        )

        self.assertIsInstance(result, ClientMetadata)
        self.assertEqual(result.source, "face")
        self.assertEqual(result.timestamp, 12.5)
        self.assertEqual(len(result.detections), 1)
        self.assertEqual(
            result.data,
            {
                "count": 1,
            },
        )

    def test_parse_metadata_rejects_invalid_timestamp(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid metadata timestamp",
        ):
            self.client._parse_metadata(
                {
                    "timestamp": "bad",
                }
            )

    def test_parse_detection_status_from_get_response(
        self,
    ) -> None:
        result = self.client._parse_detection_status(
            {
                "detectors": [
                    "color",
                    "face",
                ],
                "enabled": {
                    "color": True,
                    "face": False,
                },
            }
        )

        self.assertEqual(
            result.detectors,
            {
                "color": True,
                "face": False,
            },
        )
        self.assertIsNone(result.changed)

    def test_parse_detection_status_from_enable_response(
        self,
    ) -> None:
        result = self.client._parse_detection_status(
            {
                "enabled": "face",
                "detectors": {
                    "color": False,
                    "face": True,
                },
            }
        )

        self.assertEqual(result.changed, "face")
        self.assertTrue(result.is_enabled("face"))

    def test_parse_detection_status_from_disable_response(
        self,
    ) -> None:
        result = self.client._parse_detection_status(
            {
                "disabled": "face",
                "detectors": {
                    "face": False,
                },
            }
        )

        self.assertEqual(result.changed, "face")
        self.assertFalse(result.is_enabled("face"))

    def test_parse_detection_status_rejects_bad_shape(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid detector status",
        ):
            self.client._parse_detection_status(
                {
                    "detectors": "bad",
                }
            )

    def test_parse_stream_overlay_status(self) -> None:
        result = self.client._parse_stream_overlay_status(
            {
                "enabled": True,
                "source": "face",
            }
        )

        self.assertEqual(
            result,
            ClientStreamOverlayStatus(
                enabled=True,
                source="face",
            ),
        )

    def test_parse_statistics(self) -> None:
        result = self.client._parse_statistics(
            {
                "running": True,
                "camera": {
                    "running": True,
                    "fps": 20.0,
                    "consumer_count": 3,
                    "has_frame": True,
                    "last_error": None,
                },
                "streaming": {
                    "running": True,
                    "clients": 2,
                    "frames_received": 100,
                    "has_frame": True,
                    "overlay": {
                        "enabled": True,
                        "source": "face",
                    },
                },
                "recording": {
                    "active": False,
                    "overlay": {
                        "enabled": False,
                        "source": None,
                    },
                },
                "detection": {
                    "detectors": {
                        "color": True,
                        "face": False,
                    },
                    "metadata_sources": [
                        "color",
                    ],
                },
                "server": {
                    "host": "0.0.0.0",
                    "port": 8080,
                    "fps": 20,
                },
            }
        )

        self.assertEqual(
            result,
            ClientVisionStatistics(
                running=True,
                camera=ClientCameraStatistics(
                    running=True,
                    fps=20.0,
                    consumer_count=3,
                    has_frame=True,
                    last_error=None,
                ),
                streaming=ClientStreamingStatistics(
                    running=True,
                    clients=2,
                    frames_received=100,
                    has_frame=True,
                    overlay=ClientStreamOverlayStatus(
                        enabled=True,
                        source="face",
                    ),
                ),
                recording=ClientRecordingStatus(
                    active=False,
                    overlay=ClientStreamOverlayStatus(
                        enabled=False,
                        source=None,
                    ),
                ),
                detection=ClientDetectionStatistics(
                    detectors={
                        "color": True,
                        "face": False,
                    },
                    metadata_sources=[
                        "color",
                    ],
                ),
                server=ClientVisionServerStatistics(
                    host="0.0.0.0",
                    port=8080,
                    fps=20.0,
                ),
            ),
        )

    def test_parse_statistics_rejects_invalid_camera_fps(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid camera FPS",
        ):
            self.client._parse_statistics(
                {
                    "camera": {
                        "fps": "bad",
                    },
                }
            )

    def test_parse_statistics_rejects_invalid_stream_clients(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid streaming client count",
        ):
            self.client._parse_statistics(
                {
                    "streaming": {
                        "clients": "bad",
                    },
                }
            )

    def test_parse_statistics_rejects_invalid_server_port(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "invalid server port",
        ):
            self.client._parse_statistics(
                {
                    "server": {
                        "port": "bad",
                    },
                }
            )


class VisionClientPublicApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_statistics(self) -> None:
        data = {
            "running": False,
            "camera": {},
            "streaming": {},
            "recording": {},
            "detection": {},
            "server": {},
        }

        with patch.object(
            self.client,
            "_get",
            return_value=data,
        ) as get:
            result = self.client.statistics()

        get.assert_called_once_with("/stats")
        self.assertIsInstance(
            result,
            ClientVisionStatistics,
        )

    def test_metadata_returns_none_when_empty(self) -> None:
        with patch.object(
            self.client,
            "_get",
            return_value={},
        ) as get:
            result = self.client.metadata("face")

        self.assertIsNone(result)
        get.assert_called_once_with("/metadata?source=face")

    def test_metadata_returns_parsed_metadata(self) -> None:
        with patch.object(
            self.client,
            "_get",
            return_value={
                "source": "face",
                "timestamp": 1.0,
                "detections": [],
                "data": {},
            },
        ):
            result = self.client.metadata("face")

        self.assertIsInstance(result, ClientMetadata)
        self.assertEqual(result.source, "face")

    def test_detection_status(self) -> None:
        with patch.object(
            self.client,
            "_get",
            return_value={
                "detectors": [
                    "face",
                ],
                "enabled": {
                    "face": True,
                },
            },
        ) as get:
            result = self.client.detection_status()

        get.assert_called_once_with("/detection")
        self.assertTrue(result.is_enabled("face"))

    def test_enable_detection(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": "face",
                "detectors": {
                    "face": True,
                },
            },
        ) as post:
            result = self.client.enable_detection("face")

        post.assert_called_once_with(
            "/detection/enable",
            {
                "name": "face",
            },
        )
        self.assertEqual(result.changed, "face")

    def test_disable_detection(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "disabled": "face",
                "detectors": {
                    "face": False,
                },
            },
        ) as post:
            result = self.client.disable_detection("face")

        post.assert_called_once_with(
            "/detection/disable",
            {
                "name": "face",
            },
        )
        self.assertEqual(result.changed, "face")

    def test_enable_stream_overlay(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": True,
                "source": "face",
            },
        ) as post:
            result = self.client.enable_stream_overlay("face")

        post.assert_called_once_with(
            "/stream/overlay/enable",
            {
                "source": "face",
            },
        )
        self.assertTrue(result.enabled)
        self.assertEqual(result.source, "face")

    def test_disable_stream_overlay(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": False,
                "source": None,
            },
        ) as post:
            result = self.client.disable_stream_overlay()

        post.assert_called_once_with(
            "/stream/overlay/disable",
            {},
        )
        self.assertFalse(result.enabled)

    def test_enable_color_detection_with_multiple_colors(
        self,
    ) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": "color",
                "detectors": {
                    "color": True,
                    "face": False,
                },
            },
        ) as post:
            result = self.client.enable_color_detection(
                [
                    "red",
                    "green",
                    "blue",
                ],
                min_area=250,
            )

        post.assert_called_once_with(
            "/detection/color/enable",
            {
                "colors": [
                    "red",
                    "green",
                    "blue",
                ],
                "min_area": 250.0,
            },
        )

        self.assertEqual(result.changed, "color")
        self.assertTrue(result.is_enabled("color"))

    def test_enable_color_detection_with_single_color(
        self,
    ) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": "color",
                "detectors": {
                    "color": True,
                },
            },
        ) as post:
            self.client.enable_color_detection("yellow")

        post.assert_called_once_with(
            "/detection/color/enable",
            {
                "colors": "yellow",
            },
        )

    def test_enable_color_detection_with_current_configuration(
        self,
    ) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": "color",
                "detectors": {
                    "color": True,
                },
            },
        ) as post:
            self.client.enable_color_detection()

        post.assert_called_once_with(
            "/detection/color/enable",
            {},
        )

    def test_enable_color_detection_with_min_area_only(
        self,
    ) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": "color",
                "detectors": {
                    "color": True,
                },
            },
        ) as post:
            self.client.enable_color_detection(
                min_area=125,
            )

        post.assert_called_once_with(
            "/detection/color/enable",
            {
                "min_area": 125.0,
            },
        )

    def test_enable_color_detection_converts_sequence_to_list(
        self,
    ) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": "color",
                "detectors": {
                    "color": True,
                },
            },
        ) as post:
            self.client.enable_color_detection(
                (
                    "red",
                    "blue",
                )
            )

        post.assert_called_once_with(
            "/detection/color/enable",
            {
                "colors": [
                    "red",
                    "blue",
                ],
            },
        )


class VisionClientMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_snapshot_saves_returned_data(self) -> None:
        with TemporaryDirectory() as tmp:
            home = Path(tmp)

            with (
                patch.object(
                    Path,
                    "home",
                    return_value=home,
                ),
                patch.object(
                    self.client,
                    "_request_bytes",
                    return_value=(
                        b"image-data",
                        {
                            "X-Betabox-Format": "jpg",
                            "X-Betabox-Timestamp": "12.5",
                        },
                    ),
                ) as request_bytes,
            ):
                result = self.client.snapshot(
                    filename="photo.jpg",
                    overlay=True,
                    source="face",
                )

            self.assertEqual(
                result,
                ClientSnapshot(
                    path=home / "media" / "pictures" / "photo.jpg",
                    timestamp=12.5,
                    format="jpg",
                ),
            )
            self.assertEqual(
                result.path.read_bytes(),
                b"image-data",
            )
            request_bytes.assert_called_once_with(
                "POST",
                "/snapshot?format=jpg&overlay=true&source=face",
            )

    def test_snapshot_rejects_invalid_timestamp(
        self,
    ) -> None:
        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"image-data",
                    {
                        "X-Betabox-Timestamp": "bad",
                    },
                ),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "invalid snapshot timestamp",
            ),
        ):
            self.client.snapshot(filename="photo.jpg")

    def test_start_recording_stores_filename_after_success(
        self,
    ) -> None:
        with (
            patch.object(
                self.client,
                "_post",
            ) as post,
            patch.object(
                self.client,
                "_recording_output_path",
                return_value=Path("/tmp/lesson.mp4"),
            ),
        ):
            result = self.client.start_recording(
                filename="lesson.mp4",
                overlay=True,
                source="face",
            )

        post.assert_called_once_with(
            "/recording/start?filename=lesson.mp4&overlay=true&source=face"
        )
        self.assertEqual(
            self.client._recording_filename,
            "lesson.mp4",
        )
        self.assertEqual(
            result,
            Path("/tmp/lesson.mp4"),
        )

    def test_failed_start_does_not_store_filename(
        self,
    ) -> None:
        with (
            patch.object(
                self.client,
                "_post",
                side_effect=VisionClientError("start failed"),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "start failed",
            ),
        ):
            self.client.start_recording(filename="lesson.mp4")

        self.assertIsNone(self.client._recording_filename)

    def test_stop_recording_uses_stored_filename(
        self,
    ) -> None:
        self.client._recording_filename = "lesson.mp4"

        with TemporaryDirectory() as tmp:
            home = Path(tmp)

            with (
                patch.object(
                    Path,
                    "home",
                    return_value=home,
                ),
                patch.object(
                    self.client,
                    "_request_bytes",
                    return_value=(
                        b"video-data",
                        {
                            "X-Betabox-Format": "mp4",
                            "X-Betabox-Start-Timestamp": "1.0",
                            "X-Betabox-End-Timestamp": "3.5",
                            "X-Betabox-Frame-Count": "50",
                            "X-Betabox-FPS": "20",
                        },
                    ),
                ),
            ):
                result = self.client.stop_recording()

            self.assertEqual(
                result.path,
                home / "media" / "videos" / "lesson.mp4",
            )
            self.assertEqual(
                result.path.read_bytes(),
                b"video-data",
            )
            self.assertEqual(
                result.duration,
                2.5,
            )
            self.assertEqual(
                result.frame_count,
                50,
            )
            self.assertIsNone(self.client._recording_filename)

    def test_failed_recording_request_preserves_filename(
        self,
    ) -> None:
        self.client._recording_filename = "lesson.mp4"

        with (
            patch.object(
                self.client,
                "_request_bytes",
                side_effect=VisionClientError("stop failed"),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "stop failed",
            ),
        ):
            self.client.stop_recording()

        self.assertEqual(
            self.client._recording_filename,
            "lesson.mp4",
        )

    def test_invalid_recording_metadata_preserves_filename(
        self,
    ) -> None:
        self.client._recording_filename = "lesson.mp4"

        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"video-data",
                    {
                        "X-Betabox-Frame-Count": "bad",
                    },
                ),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "invalid recording metadata",
            ),
        ):
            self.client.stop_recording()

        self.assertEqual(
            self.client._recording_filename,
            "lesson.mp4",
        )

    def test_failed_recording_save_preserves_filename(
        self,
    ) -> None:
        self.client._recording_filename = "lesson.mp4"

        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"video-data",
                    {
                        "X-Betabox-Start-Timestamp": "1",
                        "X-Betabox-End-Timestamp": "2",
                        "X-Betabox-Frame-Count": "20",
                        "X-Betabox-FPS": "20",
                    },
                ),
            ),
            patch.object(
                self.client,
                "_recording_output_path",
                return_value=Path("/tmp/lesson.mp4"),
            ),
            patch.object(
                self.client,
                "_save_media_file",
                side_effect=VisionClientError("save failed"),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "save failed",
            ),
        ):
            self.client.stop_recording()

        self.assertEqual(
            self.client._recording_filename,
            "lesson.mp4",
        )


if __name__ == "__main__":
    unittest.main()
