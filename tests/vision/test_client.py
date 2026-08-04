from __future__ import annotations

import io
import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib import error

from betabox_robotics.vision.client import (
    ClientDetection,
    ClientDetectionStatus,
    ClientMetadata,
    ClientRecording,
    ClientSnapshot,
    ClientStreamOverlayStatus,
    ClientVisionStatistics,
    VisionClient,
    VisionClientError,
    _validate_base_url,
    _validate_timeout,
)


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        return None


def make_http_error(
    *,
    code: int = 400,
    body: bytes = b"",
) -> error.HTTPError:
    return error.HTTPError(
        url="http://127.0.0.1:8080/test",
        code=code,
        msg="error",
        hdrs=Message(),
        fp=io.BytesIO(body),
    )


class VisionClientValidationTests(unittest.TestCase):
    def test_validate_base_url(self) -> None:
        self.assertEqual(
            _validate_base_url("  http://127.0.0.1:8080/  "),
            "http://127.0.0.1:8080",
        )

    def test_validate_base_url_accepts_https(self) -> None:
        self.assertEqual(
            _validate_base_url("https://robot.example.com"),
            "https://robot.example.com",
        )

    def test_validate_base_url_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "base_url must be a string",
        ):
            _validate_base_url(
                123  # type: ignore[arg-type]
            )

    def test_validate_base_url_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "base_url cannot be empty",
        ):
            _validate_base_url(" ")

    def test_validate_base_url_rejects_invalid_url(
        self,
    ) -> None:
        for value in (
            "localhost:8080",
            "ftp://robot.example.com",
            "http://",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "valid HTTP or HTTPS URL",
                ),
            ):
                _validate_base_url(value)

    def test_validate_timeout(self) -> None:
        self.assertEqual(
            _validate_timeout(5),
            5.0,
        )

    def test_validate_timeout_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            True,
            "5",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "timeout must be a number",
                ),
            ):
                _validate_timeout(value)

    def test_validate_timeout_rejects_non_finite_value(
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
                    "timeout must be finite",
                ),
            ):
                _validate_timeout(value)

    def test_validate_timeout_rejects_non_positive_value(
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
                    "timeout must be greater than zero",
                ),
            ):
                _validate_timeout(value)

    def test_constructor(self) -> None:
        client = VisionClient(
            " http://robot.local:9000/ ",
            timeout=4,
        )

        self.assertEqual(
            client.base_url,
            "http://robot.local:9000",
        )
        self.assertEqual(
            client.timeout,
            4.0,
        )
        self.assertIsNone(client._recording_filename)

    def test_default_uses_vision_config(self) -> None:
        config = SimpleNamespace(
            service_url="http://robot.local:8080",
            request_timeout=7.5,
        )

        client = VisionClient.default(
            config  # type: ignore[arg-type]
        )

        self.assertEqual(
            client.base_url,
            "http://robot.local:8080",
        )
        self.assertEqual(
            client.timeout,
            7.5,
        )


class VisionClientDataTests(unittest.TestCase):
    def test_recording_duration(self) -> None:
        recording = ClientRecording(
            path=Path("video.mp4"),
            start_timestamp=10.0,
            end_timestamp=12.5,
            frame_count=50,
            fps=20.0,
        )

        self.assertEqual(
            recording.duration,
            2.5,
        )

    def test_recording_duration_cannot_be_negative(
        self,
    ) -> None:
        recording = ClientRecording(
            path=Path("video.mp4"),
            start_timestamp=12.0,
            end_timestamp=10.0,
            frame_count=0,
            fps=20.0,
        )

        self.assertEqual(
            recording.duration,
            0.0,
        )

    def test_detection_status_properties(self) -> None:
        status = ClientDetectionStatus(
            detectors={
                "face": False,
                "color": True,
                "objects": False,
            },
        )

        self.assertEqual(
            status.enabled,
            ["color"],
        )
        self.assertEqual(
            status.disabled,
            [
                "face",
                "objects",
            ],
        )
        self.assertTrue(status.is_enabled("color"))
        self.assertFalse(status.is_enabled("face"))
        self.assertFalse(status.is_enabled("unknown"))


class VisionClientFormatTests(unittest.TestCase):
    def test_snapshot_format_defaults_to_jpg(self) -> None:
        self.assertEqual(
            VisionClient._snapshot_format(None),
            "jpg",
        )

    def test_snapshot_format_from_filename(self) -> None:
        expected = {
            "picture": "jpg",
            "picture.jpg": "jpg",
            "picture.JPEG": "jpg",
            "picture.png": "png",
            "picture.PNG": "png",
        }

        for filename, image_format in expected.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    VisionClient._snapshot_format(filename),
                    image_format,
                )

    def test_snapshot_format_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "filename must be a string",
        ):
            VisionClient._snapshot_format(
                123  # type: ignore[arg-type]
            )

    def test_snapshot_format_rejects_empty_filename(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "filename cannot be empty",
        ):
            VisionClient._snapshot_format(" ")

    def test_snapshot_format_rejects_unsupported_suffix(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"\.jpg, \.jpeg, or \.png",
        ):
            VisionClient._snapshot_format("picture.gif")


class VisionClientMediaPathTests(unittest.TestCase):
    def test_media_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "pictures"

            path = VisionClient._media_output_path(
                directory=directory,
                filename="lesson.jpg",
                media_name="snapshot",
                extension="jpg",
            )

            self.assertEqual(
                path,
                directory / "lesson.jpg",
            )
            self.assertTrue(directory.is_dir())

    def test_media_output_path_replaces_suffix(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)

            path = VisionClient._media_output_path(
                directory=directory,
                filename="lesson.png",
                media_name="recording",
                extension="mp4",
            )

            self.assertEqual(
                path,
                directory / "lesson.mp4",
            )

    def test_media_output_path_generates_filename(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)

            path = VisionClient._media_output_path(
                directory=directory,
                filename=None,
                media_name="snapshot",
                extension="jpg",
            )

            self.assertEqual(
                path.parent,
                directory,
            )
            self.assertTrue(path.name.startswith("snapshot_"))
            self.assertEqual(
                path.suffix,
                ".jpg",
            )

    def test_media_output_path_rejects_directory_components(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            self.assertRaisesRegex(
                VisionClientError,
                "plain filename",
            ),
        ):
            VisionClient._media_output_path(
                directory=Path(temp_dir),
                filename="../picture.jpg",
                media_name="snapshot",
                extension="jpg",
            )

    def test_media_output_path_rejects_empty_filename(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            self.assertRaisesRegex(
                VisionClientError,
                "plain filename",
            ),
        ):
            VisionClient._media_output_path(
                directory=Path(temp_dir),
                filename=" ",
                media_name="snapshot",
                extension="jpg",
            )

    def test_media_output_path_wraps_directory_failure(
        self,
    ) -> None:
        with (
            patch(
                "betabox_robotics.vision.client.Path.mkdir",
                side_effect=OSError("permission denied"),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "failed to create media directory",
            ),
        ):
            VisionClient._media_output_path(
                directory=Path("/pictures"),
                filename="picture.jpg",
                media_name="snapshot",
                extension="jpg",
            )

    def test_save_media_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "picture.jpg"

            VisionClient._save_media_file(
                path,
                b"image-data",
                "snapshot",
            )

            self.assertEqual(
                path.read_bytes(),
                b"image-data",
            )

    def test_save_media_file_wraps_failure(
        self,
    ) -> None:
        with (
            patch(
                "betabox_robotics.vision.client.Path.write_bytes",
                side_effect=OSError("permission denied"),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "failed to save snapshot",
            ),
        ):
            VisionClient._save_media_file(
                Path("/picture.jpg"),
                b"data",
                "snapshot",
            )


class VisionClientQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_path_with_query(self) -> None:
        result = self.client._path_with_query(
            "/snapshot",
            {
                "format": "png",
                "overlay": "true",
                "source": "face detection",
            },
        )

        self.assertEqual(
            result,
            ("/snapshot?format=png&overlay=true&source=face+detection"),
        )

    def test_path_with_query_omits_none(self) -> None:
        result = self.client._path_with_query(
            "/metadata",
            {
                "source": None,
            },
        )

        self.assertEqual(
            result,
            "/metadata",
        )


class VisionClientRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient(
            timeout=3,
        )

    def test_request_returns_data(self) -> None:
        response = FakeResponse(
            json.dumps(
                {
                    "success": True,
                    "data": {
                        "value": 10,
                    },
                }
            ).encode("utf-8")
        )

        with patch(
            "betabox_robotics.vision.client.request.urlopen",
            return_value=response,
        ) as urlopen:
            result = self.client._request(
                "GET",
                "/stats",
            )

        self.assertEqual(
            result,
            {
                "value": 10,
            },
        )

        req = urlopen.call_args.args[0]

        self.assertEqual(
            req.full_url,
            "http://127.0.0.1:8080/stats",
        )
        self.assertEqual(
            req.method,
            "GET",
        )
        urlopen.assert_called_once_with(
            req,
            timeout=3.0,
        )

    def test_request_sends_json(self) -> None:
        response = FakeResponse(b'{"success": true, "data": {}}')

        with patch(
            "betabox_robotics.vision.client.request.urlopen",
            return_value=response,
        ) as urlopen:
            self.client._request(
                "POST",
                "/detection/enable",
                data={
                    "name": "face",
                },
            )

        req = urlopen.call_args.args[0]

        self.assertEqual(
            req.method,
            "POST",
        )
        self.assertEqual(
            json.loads(req.data.decode("utf-8")),
            {
                "name": "face",
            },
        )
        self.assertEqual(
            req.headers["Content-type"],
            "application/json",
        )

    def test_request_accepts_empty_success_payload(
        self,
    ) -> None:
        response = FakeResponse(b'{"success": true}')

        with patch(
            "betabox_robotics.vision.client.request.urlopen",
            return_value=response,
        ):
            result = self.client._request(
                "POST",
                "/test",
            )

        self.assertEqual(
            result,
            {},
        )

    def test_request_rejects_invalid_json(self) -> None:
        response = FakeResponse(b"not-json")

        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                return_value=response,
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "invalid Vision service response",
            ),
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    def test_request_rejects_non_object_response(
        self,
    ) -> None:
        response = FakeResponse(b'["unexpected"]')

        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                return_value=response,
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "unexpected response",
            ),
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    def test_request_rejects_failed_response(
        self,
    ) -> None:
        response = FakeResponse(b'{"success": false, "error": "camera unavailable"}')

        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                return_value=response,
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "camera unavailable",
            ),
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    def test_request_rejects_invalid_payload(
        self,
    ) -> None:
        response = FakeResponse(b'{"success": true, "data": []}')

        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                return_value=response,
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "returned invalid data",
            ),
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    def test_request_handles_http_error_json(
        self,
    ) -> None:
        failure = make_http_error(
            code=400,
            body=(b'{"success": false, "error": "bad request"}'),
        )

        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                side_effect=failure,
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "bad request",
            ),
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    def test_request_handles_http_error_without_json(
        self,
    ) -> None:
        failure = make_http_error(
            code=500,
            body=b"server error",
        )

        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                side_effect=failure,
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "HTTP 500",
            ),
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    def test_request_handles_url_error(self) -> None:
        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                side_effect=error.URLError("connection refused"),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "betabox-video.service",
            ),
        ):
            self.client._request(
                "GET",
                "/stats",
            )

    def test_request_bytes(self) -> None:
        response = FakeResponse(
            b"binary-data",
            headers={
                "X-Test": "value",
            },
        )

        with patch(
            "betabox_robotics.vision.client.request.urlopen",
            return_value=response,
        ):
            body, headers = self.client._request_bytes(
                "POST",
                "/snapshot",
            )

        self.assertEqual(
            body,
            b"binary-data",
        )
        self.assertEqual(
            headers["X-Test"],
            "value",
        )

    def test_request_bytes_handles_http_error(
        self,
    ) -> None:
        failure = make_http_error(
            body=b'{"error": "snapshot failed"}',
        )

        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                side_effect=failure,
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "snapshot failed",
            ),
        ):
            self.client._request_bytes(
                "POST",
                "/snapshot",
            )

    def test_request_bytes_handles_url_error(
        self,
    ) -> None:
        with (
            patch(
                "betabox_robotics.vision.client.request.urlopen",
                side_effect=error.URLError("connection refused"),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "betabox-video.service",
            ),
        ):
            self.client._request_bytes(
                "POST",
                "/snapshot",
            )


class VisionClientSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_snapshot(self) -> None:
        output_path = Path("/media/pictures/lesson.png")

        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"image-data",
                    {
                        "X-Betabox-Format": "png",
                        "X-Betabox-Timestamp": "123.5",
                    },
                ),
            ) as request_bytes,
            patch.object(
                self.client,
                "_media_output_path",
                return_value=output_path,
            ) as media_path,
            patch.object(
                self.client,
                "_save_media_file",
            ) as save,
        ):
            result = self.client.snapshot(
                filename="lesson.png",
                overlay=True,
                source="color",
            )

        self.assertEqual(
            result,
            ClientSnapshot(
                path=output_path,
                timestamp=123.5,
                format="png",
            ),
        )
        request_bytes.assert_called_once_with(
            "POST",
            ("/snapshot?format=png&overlay=true&source=color"),
        )
        media_path.assert_called_once_with(
            directory=Path.home() / "media" / "pictures",
            filename="lesson.png",
            media_name="snapshot",
            extension="png",
        )
        save.assert_called_once_with(
            output_path,
            b"image-data",
            "snapshot",
        )

    def test_snapshot_defaults_to_jpg(self) -> None:
        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"image",
                    {
                        "X-Betabox-Format": "jpg",
                        "X-Betabox-Timestamp": "1.0",
                    },
                ),
            ) as request_bytes,
            patch.object(
                self.client,
                "_media_output_path",
                return_value=Path("/media/picture.jpg"),
            ),
            patch.object(
                self.client,
                "_save_media_file",
            ),
        ):
            result = self.client.snapshot()

        self.assertEqual(
            result.format,
            "jpg",
        )
        request_bytes.assert_called_once_with(
            "POST",
            "/snapshot?format=jpg",
        )

    def test_snapshot_rejects_invalid_returned_format(
        self,
    ) -> None:
        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"image",
                    {
                        "X-Betabox-Format": "gif",
                        "X-Betabox-Timestamp": "1.0",
                    },
                ),
            ),
            self.assertRaisesRegex(
                ValueError,
                "snapshot filename",
            ),
        ):
            self.client.snapshot()

    def test_snapshot_rejects_invalid_timestamp(
        self,
    ) -> None:
        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"image",
                    {
                        "X-Betabox-Format": "jpg",
                        "X-Betabox-Timestamp": "nan",
                    },
                ),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "snapshot timestamp",
            ),
        ):
            self.client.snapshot()


class VisionClientRecordingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_start_recording(self) -> None:
        output_path = Path("/media/videos/lesson.mp4")

        with (
            patch.object(
                self.client,
                "_recording_output_path",
                return_value=output_path,
            ) as recording_path,
            patch.object(
                self.client,
                "_post",
                return_value={},
            ) as post,
        ):
            result = self.client.start_recording(
                filename="lesson.mp4",
                overlay=True,
                source="face",
            )

        self.assertEqual(
            result,
            output_path,
        )
        recording_path.assert_called_once_with("lesson.mp4")
        post.assert_called_once_with(
            "/recording/start?filename=lesson.mp4&overlay=true&source=face"
        )
        self.assertEqual(
            self.client._recording_filename,
            "lesson.mp4",
        )

    def test_start_recording_validates_path_before_request(
        self,
    ) -> None:
        with (
            patch.object(
                self.client,
                "_recording_output_path",
                side_effect=VisionClientError("invalid filename"),
            ),
            patch.object(
                self.client,
                "_post",
            ) as post,
            self.assertRaisesRegex(
                VisionClientError,
                "invalid filename",
            ),
        ):
            self.client.start_recording(filename="../bad.mp4")

        post.assert_not_called()

    def test_stop_recording(self) -> None:
        self.client._recording_filename = "lesson.mp4"
        output_path = Path("/media/videos/lesson.mp4")

        headers = {
            "X-Betabox-Format": "mp4",
            "X-Betabox-Start-Timestamp": "10.0",
            "X-Betabox-End-Timestamp": "12.5",
            "X-Betabox-Frame-Count": "50",
            "X-Betabox-FPS": "20.0",
        }

        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"video-data",
                    headers,
                ),
            ) as request_bytes,
            patch.object(
                self.client,
                "_recording_output_path",
                return_value=output_path,
            ) as recording_path,
            patch.object(
                self.client,
                "_save_media_file",
            ) as save,
        ):
            result = self.client.stop_recording()

        self.assertEqual(
            result,
            ClientRecording(
                path=output_path,
                start_timestamp=10.0,
                end_timestamp=12.5,
                frame_count=50,
                fps=20.0,
            ),
        )
        self.assertEqual(
            result.duration,
            2.5,
        )
        request_bytes.assert_called_once_with(
            "POST",
            "/recording/stop",
        )
        recording_path.assert_called_once_with("lesson.mp4")
        save.assert_called_once_with(
            output_path,
            b"video-data",
            "recording",
        )
        self.assertIsNone(self.client._recording_filename)

    def test_stop_recording_explicit_filename_overrides_stored(
        self,
    ) -> None:
        self.client._recording_filename = "stored.mp4"

        headers = {
            "X-Betabox-Format": "mp4",
            "X-Betabox-Start-Timestamp": "1",
            "X-Betabox-End-Timestamp": "2",
            "X-Betabox-Frame-Count": "20",
            "X-Betabox-FPS": "20",
        }

        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"video",
                    headers,
                ),
            ),
            patch.object(
                self.client,
                "_recording_output_path",
                return_value=Path("/explicit.mp4"),
            ) as recording_path,
            patch.object(
                self.client,
                "_save_media_file",
            ),
        ):
            self.client.stop_recording(filename="explicit.mp4")

        recording_path.assert_called_once_with("explicit.mp4")

    def test_stop_recording_rejects_invalid_format(
        self,
    ) -> None:
        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"video",
                    {
                        "X-Betabox-Format": "avi",
                    },
                ),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "invalid recording format",
            ),
        ):
            self.client.stop_recording()

    def test_stop_recording_rejects_invalid_metadata(
        self,
    ) -> None:
        headers = {
            "X-Betabox-Format": "mp4",
            "X-Betabox-Start-Timestamp": "nan",
            "X-Betabox-End-Timestamp": "2",
            "X-Betabox-Frame-Count": "20",
            "X-Betabox-FPS": "20",
        }

        with (
            patch.object(
                self.client,
                "_request_bytes",
                return_value=(
                    b"video",
                    headers,
                ),
            ),
            self.assertRaisesRegex(
                VisionClientError,
                "recording start timestamp",
            ),
        ):
            self.client.stop_recording()


class VisionClientDetectionAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_metadata_returns_none(self) -> None:
        with patch.object(
            self.client,
            "_get",
            return_value={},
        ) as get:
            result = self.client.metadata("color")

        self.assertIsNone(result)
        get.assert_called_once_with("/metadata?source=color")

    def test_metadata(self) -> None:
        payload = {
            "source": "color",
            "timestamp": 123.5,
            "detections": [],
            "data": {
                "count": 0,
            },
        }

        with patch.object(
            self.client,
            "_get",
            return_value=payload,
        ):
            result = self.client.metadata("color")

        self.assertEqual(
            result,
            ClientMetadata(
                source="color",
                timestamp=123.5,
                detections=[],
                data={
                    "count": 0,
                },
            ),
        )

    def test_detection_status(self) -> None:
        with patch.object(
            self.client,
            "_get",
            return_value={
                "detectors": [
                    "color",
                    "face",
                ],
                "enabled": {
                    "color": True,
                    "face": False,
                },
            },
        ):
            status = self.client.detection_status()

        self.assertEqual(
            status.detectors,
            {
                "color": True,
                "face": False,
            },
        )

    def test_enable_detection(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "detectors": {
                    "color": False,
                    "face": True,
                },
                "enabled": "face",
            },
        ) as post:
            status = self.client.enable_detection("face")

        post.assert_called_once_with(
            "/detection/enable",
            {
                "name": "face",
            },
        )
        self.assertEqual(
            status.changed,
            "face",
        )
        self.assertTrue(status.is_enabled("face"))

    def test_disable_detection(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "detectors": {
                    "color": True,
                    "face": False,
                },
                "disabled": "face",
            },
        ) as post:
            status = self.client.disable_detection("face")

        post.assert_called_once_with(
            "/detection/disable",
            {
                "name": "face",
            },
        )
        self.assertEqual(
            status.changed,
            "face",
        )

    def test_enable_color_detection(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "detectors": {
                    "color": True,
                },
                "enabled": "color",
            },
        ) as post:
            status = self.client.enable_color_detection(
                [
                    "red",
                    "blue",
                ],
                min_area=25,
            )

        post.assert_called_once_with(
            "/detection/color/enable",
            {
                "colors": [
                    "red",
                    "blue",
                ],
                "min_area": 25,
            },
        )
        self.assertTrue(status.is_enabled("color"))

    def test_enable_color_detection_rejects_invalid_min_area(
        self,
    ) -> None:
        for value in (
            True,
            "25",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "min_area must be a number",
                ),
            ):
                self.client.enable_color_detection(
                    min_area=value,  # type: ignore[arg-type]
                )


class VisionClientOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_enable_stream_overlay(self) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": True,
                "source": "color",
            },
        ) as post:
            result = self.client.enable_stream_overlay("color")

        self.assertEqual(
            result,
            ClientStreamOverlayStatus(
                enabled=True,
                source="color",
            ),
        )
        post.assert_called_once_with(
            "/stream/overlay/enable",
            {
                "source": "color",
            },
        )

    def test_enable_stream_overlay_without_source(
        self,
    ) -> None:
        with patch.object(
            self.client,
            "_post_json",
            return_value={
                "enabled": True,
                "source": None,
            },
        ) as post:
            result = self.client.enable_stream_overlay()

        self.assertTrue(result.enabled)
        self.assertIsNone(result.source)
        post.assert_called_once_with(
            "/stream/overlay/enable",
            {},
        )

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

        self.assertEqual(
            result,
            ClientStreamOverlayStatus(
                enabled=False,
                source=None,
            ),
        )
        post.assert_called_once_with(
            "/stream/overlay/disable",
            {},
        )


class VisionClientParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

    def test_parse_float(self) -> None:
        self.assertEqual(
            self.client._parse_float(
                "1.5",
                field="value",
            ),
            1.5,
        )

    def test_parse_float_rejects_invalid_values(
        self,
    ) -> None:
        for value in (
            True,
            "bad",
            float("nan"),
            float("inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    VisionClientError,
                    "invalid value",
                ),
            ):
                self.client._parse_float(
                    value,
                    field="value",
                )

    def test_parse_int(self) -> None:
        self.assertEqual(
            self.client._parse_int(
                "10",
                field="count",
            ),
            10,
        )
        self.assertEqual(
            self.client._parse_int(
                10.0,
                field="count",
            ),
            10,
        )

    def test_parse_int_rejects_invalid_values(
        self,
    ) -> None:
        for value in (
            True,
            1.5,
            "bad",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    VisionClientError,
                    "invalid count",
                ),
            ):
                self.client._parse_int(
                    value,
                    field="count",
                )

    def test_parse_bool(self) -> None:
        self.assertTrue(
            self.client._parse_bool(
                True,
                field="state",
            )
        )
        self.assertFalse(
            self.client._parse_bool(
                False,
                field="state",
            )
        )

    def test_parse_bool_rejects_non_boolean(
        self,
    ) -> None:
        for value in (
            1,
            "false",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    VisionClientError,
                    "invalid state",
                ),
            ):
                self.client._parse_bool(
                    value,
                    field="state",
                )

    def test_parse_string(self) -> None:
        self.assertEqual(
            self.client._parse_string(
                " color ",
                field="name",
            ),
            "color",
        )

    def test_parse_string_rejects_invalid_value(
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
                    VisionClientError,
                    "invalid name",
                ),
            ):
                self.client._parse_string(
                    value,
                    field="name",
                )

    def test_parse_detection(self) -> None:
        result = self.client._parse_detection(
            {
                "label": "face",
                "confidence": 0.75,
                "box": [
                    10,
                    20,
                    30,
                    40,
                ],
                "center": [
                    25,
                    40,
                ],
                "data": {
                    "width": 30,
                },
            }
        )

        self.assertEqual(
            result,
            ClientDetection(
                label="face",
                confidence=0.75,
                box=(
                    10,
                    20,
                    30,
                    40,
                ),
                center=(
                    25,
                    40,
                ),
                data={
                    "width": 30,
                },
            ),
        )

    def test_parse_detection_without_optional_values(
        self,
    ) -> None:
        result = self.client._parse_detection(
            {
                "label": "red",
            }
        )

        self.assertEqual(
            result,
            ClientDetection(
                label="red",
                confidence=None,
                box=None,
                center=None,
                data={},
            ),
        )

    def test_parse_detection_rejects_invalid_label(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "detection label",
        ):
            self.client._parse_detection(
                {
                    "label": 123,
                }
            )

    def test_parse_detection_rejects_invalid_box(
        self,
    ) -> None:
        for box in (
            [1, 2],
            "box",
            [
                1,
                2,
                3,
                "bad",
            ],
        ):
            with (
                self.subTest(box=box),
                self.assertRaisesRegex(
                    VisionClientError,
                    "detection box",
                ),
            ):
                self.client._parse_detection(
                    {
                        "label": "face",
                        "box": box,
                    }
                )

    def test_parse_detection_rejects_invalid_center(
        self,
    ) -> None:
        for center in (
            [1],
            "center",
            [
                1,
                "bad",
            ],
        ):
            with (
                self.subTest(center=center),
                self.assertRaisesRegex(
                    VisionClientError,
                    "detection center",
                ),
            ):
                self.client._parse_detection(
                    {
                        "label": "face",
                        "center": center,
                    }
                )

    def test_parse_metadata(self) -> None:
        result = self.client._parse_metadata(
            {
                "source": "face",
                "timestamp": 100.5,
                "detections": [
                    {
                        "label": "face",
                        "box": [
                            1,
                            2,
                            3,
                            4,
                        ],
                    },
                ],
                "data": {
                    "count": 1,
                },
            }
        )

        self.assertEqual(
            result.source,
            "face",
        )
        self.assertEqual(
            result.timestamp,
            100.5,
        )
        self.assertEqual(
            len(result.detections),
            1,
        )
        self.assertEqual(
            result.data,
            {
                "count": 1,
            },
        )

    def test_parse_metadata_rejects_invalid_source(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "metadata source",
        ):
            self.client._parse_metadata(
                {
                    "source": 123,
                }
            )

    def test_parse_detection_status_from_names(
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

    def test_parse_detection_status_from_map(
        self,
    ) -> None:
        result = self.client._parse_detection_status(
            {
                "detectors": {
                    "color": True,
                    "face": False,
                },
                "enabled": "color",
            }
        )

        self.assertEqual(
            result.changed,
            "color",
        )

    def test_parse_detection_status_rejects_invalid_boolean(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "color detector state",
        ):
            self.client._parse_detection_status(
                {
                    "detectors": {
                        "color": "true",
                    },
                }
            )

    def test_parse_stream_overlay_status(self) -> None:
        result = self.client._parse_stream_overlay_status(
            {
                "enabled": True,
                "source": "color",
            }
        )

        self.assertEqual(
            result,
            ClientStreamOverlayStatus(
                enabled=True,
                source="color",
            ),
        )

    def test_parse_stream_overlay_rejects_invalid_state(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            VisionClientError,
            "stream overlay enabled state",
        ):
            self.client._parse_stream_overlay_status(
                {
                    "enabled": "true",
                }
            )


class VisionClientStatisticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VisionClient()

        self.payload = {
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
                    "source": "color",
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

    def test_parse_statistics(self) -> None:
        result = self.client._parse_statistics(self.payload)

        self.assertIsInstance(
            result,
            ClientVisionStatistics,
        )
        self.assertTrue(result.running)
        self.assertTrue(result.camera.running)
        self.assertEqual(
            result.camera.fps,
            20.0,
        )
        self.assertEqual(
            result.streaming.clients,
            2,
        )
        self.assertTrue(result.streaming.overlay.enabled)
        self.assertFalse(result.recording.active)
        self.assertEqual(
            result.detection.metadata_sources,
            ["color"],
        )
        self.assertEqual(
            result.server.host,
            "0.0.0.0",
        )
        self.assertEqual(
            result.server.port,
            8080,
        )

    def test_statistics_requests_stats_endpoint(
        self,
    ) -> None:
        with patch.object(
            self.client,
            "_get",
            return_value=self.payload,
        ) as get:
            result = self.client.statistics()

        self.assertIsInstance(
            result,
            ClientVisionStatistics,
        )
        get.assert_called_once_with("/stats")

    def test_parse_statistics_rejects_string_boolean(
        self,
    ) -> None:
        self.payload["running"] = "true"

        with self.assertRaisesRegex(
            VisionClientError,
            "Vision running state",
        ):
            self.client._parse_statistics(self.payload)

    def test_parse_statistics_rejects_invalid_server_host(
        self,
    ) -> None:
        self.payload["server"]["host"] = 123

        with self.assertRaisesRegex(
            VisionClientError,
            "server host",
        ):
            self.client._parse_statistics(self.payload)

    def test_parse_statistics_rejects_invalid_metadata_source(
        self,
    ) -> None:
        self.payload["detection"]["metadata_sources"] = [
            123,
        ]

        with self.assertRaisesRegex(
            VisionClientError,
            "metadata source",
        ):
            self.client._parse_statistics(self.payload)


if __name__ == "__main__":
    unittest.main()
