from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from time import strftime
from typing import (
    TYPE_CHECKING,
    Literal,
    Protocol,
    Self,
    TypeAlias,
    cast,
)
from urllib import error, parse, request

if TYPE_CHECKING:
    from betabox_robotics.robots.config import VisionConfig

ClientSnapshotFormat = Literal[
    "jpg",
    "png",
]

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]

QueryValue: TypeAlias = str | int | float | bool | None
QueryParams: TypeAlias = dict[str, QueryValue]


def _validate_base_url(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("base_url must be a string")

    base_url = value.strip().rstrip("/")

    if not base_url:
        raise ValueError("base_url cannot be empty")

    parsed = parse.urlparse(base_url)

    if (
        parsed.scheme
        not in {
            "http",
            "https",
        }
        or not parsed.netloc
    ):
        raise ValueError("base_url must be a valid HTTP or HTTPS URL")

    return base_url


def _validate_timeout(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("timeout must be a number")

    timeout = float(value)

    if not math.isfinite(timeout):
        raise ValueError("timeout must be finite")

    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    return timeout


class _HTTPResponse(Protocol):
    headers: Message

    def read(self) -> bytes: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None: ...


class VisionClientError(Exception):
    """Raised when the managed Vision service cannot complete a request."""


@dataclass(frozen=True, slots=True)
class ClientSnapshot:
    path: Path
    timestamp: float
    format: ClientSnapshotFormat


@dataclass(frozen=True, slots=True)
class ClientRecording:
    path: Path
    start_timestamp: float
    end_timestamp: float
    frame_count: int
    fps: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_timestamp - self.start_timestamp)


@dataclass(frozen=True, slots=True)
class ClientDetection:
    label: str
    confidence: float | None
    box: tuple[int, int, int, int] | None
    center: tuple[int, int] | None
    data: JSONObject


@dataclass(frozen=True, slots=True)
class ClientMetadata:
    source: str
    timestamp: float
    detections: list[ClientDetection]
    data: JSONObject


@dataclass(frozen=True, slots=True)
class ClientDetectionStatus:
    detectors: dict[str, bool]
    changed: str | None = None

    @property
    def enabled(self) -> list[str]:
        return sorted(name for name, is_enabled in self.detectors.items() if is_enabled)

    @property
    def disabled(self) -> list[str]:
        return sorted(
            name for name, is_enabled in self.detectors.items() if not is_enabled
        )

    def is_enabled(self, name: str) -> bool:
        return self.detectors.get(name, False)


@dataclass(frozen=True, slots=True)
class ClientStreamOverlayStatus:
    enabled: bool
    source: str | None = None


@dataclass(frozen=True, slots=True)
class ClientCameraStatistics:
    running: bool
    fps: float
    consumer_count: int
    has_frame: bool
    last_error: str | None


@dataclass(frozen=True, slots=True)
class ClientStreamingStatistics:
    running: bool
    clients: int
    frames_received: int
    has_frame: bool
    overlay: ClientStreamOverlayStatus


@dataclass(frozen=True, slots=True)
class ClientRecordingStatus:
    active: bool
    overlay: ClientStreamOverlayStatus


@dataclass(frozen=True, slots=True)
class ClientDetectionStatistics:
    detectors: dict[str, bool]
    metadata_sources: list[str]


@dataclass(frozen=True, slots=True)
class ClientVisionServerStatistics:
    host: str
    port: int
    fps: float


@dataclass(frozen=True, slots=True)
class ClientVisionStatistics:
    running: bool
    camera: ClientCameraStatistics
    streaming: ClientStreamingStatistics
    recording: ClientRecordingStatus
    detection: ClientDetectionStatistics
    server: ClientVisionServerStatistics


class VisionClient:
    """
    Client for the managed Betabox Vision service.

    This does not open the camera. It talks to betabox-video.service.
    """

    base_url: str
    timeout: float
    _recording_filename: str | None

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        *,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = _validate_base_url(base_url)
        self.timeout = _validate_timeout(timeout)
        self._recording_filename = None

    @staticmethod
    def _snapshot_format(
        filename: str | None,
    ) -> ClientSnapshotFormat:
        if filename is None:
            return "jpg"

        filename_value = filename.strip()

        if not filename_value:
            raise ValueError("filename cannot be empty")

        suffix = Path(filename_value).suffix.casefold()

        if suffix in {
            ".jpg",
            ".jpeg",
            "",
        }:
            return "jpg"

        if suffix == ".png":
            return "png"

        raise ValueError("snapshot filename must use .jpg, .jpeg, or .png")

    def _request_bytes(
        self,
        method: str,
        path: str,
    ) -> tuple[bytes, Message]:
        url = f"{self.base_url}{path}"

        req = request.Request(
            url,
            method=method,
        )

        try:
            response = cast(
                _HTTPResponse,
                cast(
                    object,
                    request.urlopen(
                        req,
                        timeout=self.timeout,
                    ),
                ),
            )

            with response:
                response_body = response.read()
                response_headers = response.headers

        except error.HTTPError as exc:
            response_body_text = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            try:
                raw_error_data = cast(
                    object,
                    json.loads(response_body_text),
                )

                if not isinstance(raw_error_data, dict):
                    raise VisionClientError(
                        f"Vision service request failed with HTTP {exc.code}"
                    ) from exc

                error_data = cast(
                    JSONObject,
                    raw_error_data,
                )
            except json.JSONDecodeError:
                raise VisionClientError(
                    f"Vision service request failed with HTTP {exc.code}"
                ) from exc

            raise VisionClientError(
                str(
                    error_data.get(
                        "error",
                        f"HTTP {exc.code}",
                    )
                )
            ) from exc

        except error.URLError as exc:
            raise VisionClientError(
                "Betabox Vision service is not available. Run: sudo systemctl start betabox-video.service"
            ) from exc

        return (
            response_body,
            response_headers,
        )

    @staticmethod
    def _media_output_path(
        *,
        directory: Path,
        filename: str | None,
        media_name: str,
        extension: str,
    ) -> Path:
        try:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise VisionClientError(
                f"failed to create media directory: {directory}: {exc}"
            ) from exc

        if filename is None:
            filename = f"{media_name}_{strftime('%Y%m%d_%H%M%S')}.{extension}"
        else:
            filename = filename.strip()
            filename_path = Path(filename)

            if filename_path.name != filename or not filename:
                raise VisionClientError(
                    f"{media_name} filename must be a plain filename without directory components"
                )

        output_path = directory / filename

        if output_path.suffix.lower() != f".{extension}":
            output_path = output_path.with_suffix(f".{extension}")

        return output_path

    def _recording_output_path(
        self,
        filename: str | None,
    ) -> Path:
        return self._media_output_path(
            directory=Path.home() / "media" / "videos",
            filename=filename,
            media_name="recording",
            extension="mp4",
        )

    @staticmethod
    def _save_media_file(
        output_path: Path,
        data: bytes,
        media_name: str,
    ) -> None:
        try:
            _ = output_path.write_bytes(data)
        except OSError as exc:
            raise VisionClientError(
                f"failed to save {media_name}: {output_path}: {exc}"
            ) from exc

    @classmethod
    def default(
        cls,
        config: VisionConfig,
    ) -> VisionClient:
        return cls(
            base_url=config.service_url,
            timeout=config.request_timeout,
        )

    def statistics(self) -> ClientVisionStatistics:
        data = self._get("/stats")
        return self._parse_statistics(data)

    def snapshot(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> ClientSnapshot:
        image_format = self._snapshot_format(
            filename,
        )

        path = self._path_with_query(
            "/snapshot",
            {
                "format": image_format,
                "overlay": ("true" if overlay else None),
                "source": source,
            },
        )

        image_data, headers = self._request_bytes(
            "POST",
            path,
        )

        returned_format = self._snapshot_format(
            f"snapshot.{headers.get('X-Betabox-Format', image_format)}"
        )

        timestamp = self._parse_float(
            headers.get(
                "X-Betabox-Timestamp",
                "0",
            ),
            field="snapshot timestamp",
        )

        output_path = self._media_output_path(
            directory=Path.home() / "media" / "pictures",
            filename=filename,
            media_name="snapshot",
            extension=returned_format,
        )

        self._save_media_file(
            output_path,
            image_data,
            "snapshot",
        )

        return ClientSnapshot(
            path=output_path,
            timestamp=timestamp,
            format=returned_format,
        )

    def start_recording(
        self,
        *,
        filename: str | None = None,
        overlay: bool = False,
        source: str | None = None,
    ) -> Path:
        path = self._path_with_query(
            "/recording/start",
            {
                "filename": filename,
                "overlay": "true" if overlay else None,
                "source": source,
            },
        )

        output_path = self._recording_output_path(filename)

        _ = self._post(path)

        self._recording_filename = filename

        return output_path

    def stop_recording(
        self,
        *,
        filename: str | None = None,
    ) -> ClientRecording:
        stored_filename = self._recording_filename

        if filename is None:
            filename = stored_filename

        video_data, headers = self._request_bytes(
            "POST",
            "/recording/stop",
        )

        returned_format = headers.get(
            "X-Betabox-Format",
            "mp4",
        ).lower()

        if returned_format != "mp4":
            raise VisionClientError("Vision service returned invalid recording format")

        try:
            start_timestamp = self._parse_float(
                headers.get("X-Betabox-Start-Timestamp", "0"),
                field="recording start timestamp",
            )

            end_timestamp = self._parse_float(
                headers.get("X-Betabox-End-Timestamp", "0"),
                field="recording end timestamp",
            )

            frame_count = self._parse_int(
                headers.get("X-Betabox-Frame-Count", "0"),
                field="recording frame count",
            )

            fps = self._parse_float(
                headers.get("X-Betabox-FPS", "0"),
                field="recording FPS",
            )
        except (TypeError, ValueError) as exc:
            raise VisionClientError(
                "Vision service returned invalid recording metadata"
            ) from exc

        output_path = self._recording_output_path(filename)

        self._save_media_file(
            output_path,
            video_data,
            "recording",
        )

        self._recording_filename = None

        return ClientRecording(
            path=output_path,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            frame_count=frame_count,
            fps=fps,
        )

    def metadata(
        self,
        source: str | None = None,
    ) -> ClientMetadata | None:
        path = self._path_with_query(
            "/metadata",
            {"source": source},
        )

        data = self._get(path)

        if not data:
            return None

        return self._parse_metadata(data)

    def detection_status(self) -> ClientDetectionStatus:
        data = self._get("/detection")
        return self._parse_detection_status(data)

    def enable_detection(self, name: str) -> ClientDetectionStatus:
        data = self._post_json(
            "/detection/enable",
            {"name": name},
        )
        return self._parse_detection_status(data)

    def enable_color_detection(
        self,
        colors: str | Sequence[str] | None = None,
        *,
        min_area: float | None = None,
    ) -> ClientDetectionStatus:
        payload: JSONObject = {}

        if colors is not None:
            payload["colors"] = colors if isinstance(colors, str) else list(colors)

        if min_area is not None:
            payload["min_area"] = min_area

        data = self._post_json(
            "/detection/color/enable",
            payload,
        )

        return self._parse_detection_status(data)

    def disable_detection(self, name: str) -> ClientDetectionStatus:
        data = self._post_json(
            "/detection/disable",
            {"name": name},
        )
        return self._parse_detection_status(data)

    def enable_stream_overlay(
        self,
        source: str | None = None,
    ) -> ClientStreamOverlayStatus:
        payload: JSONObject = {}

        if source is not None:
            payload["source"] = source

        data = self._post_json(
            "/stream/overlay/enable",
            payload,
        )

        return self._parse_stream_overlay_status(data)

    def disable_stream_overlay(
        self,
    ) -> ClientStreamOverlayStatus:
        data = self._post_json(
            "/stream/overlay/disable",
            {},
        )

        return self._parse_stream_overlay_status(data)

    def _get(self, path: str) -> JSONObject:
        return self._request("GET", path)

    def _post(self, path: str) -> JSONObject:
        return self._request("POST", path)

    def _post_json(self, path: str, data: JSONObject) -> JSONObject:
        return self._request("POST", path, data=data)

    def _request(
        self,
        method: str,
        path: str,
        data: JSONObject | None = None,
    ) -> JSONObject:
        url = f"{self.base_url}{path}"

        body: bytes | None = None
        headers: dict[str, str] = {}

        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(
            url,
            data=body,
            headers=headers,
            method=method,
        )

        try:
            response = cast(
                _HTTPResponse,
                cast(
                    object,
                    request.urlopen(
                        req,
                        timeout=self.timeout,
                    ),
                ),
            )

            with response:
                response_body = response.read().decode("utf-8")

        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8")

            try:
                raw_error_data = cast(
                    object,
                    json.loads(response_body),
                )

                if not isinstance(raw_error_data, dict):
                    raise VisionClientError(
                        f"Vision service request failed with HTTP {exc.code}"
                    ) from exc

                error_data = cast(
                    JSONObject,
                    raw_error_data,
                )

            except json.JSONDecodeError:
                raise VisionClientError(
                    f"Vision service request failed with HTTP {exc.code}"
                ) from exc

            message = error_data.get(
                "error",
                f"HTTP {exc.code}",
            )

            raise VisionClientError(str(message)) from exc

        try:
            raw_response_data = cast(
                object,
                json.loads(response_body),
            )
        except json.JSONDecodeError as exc:
            raise VisionClientError("Vision service returned invalid JSON") from exc

        if not isinstance(raw_response_data, dict):
            raise VisionClientError("Vision service returned an unexpected response")

        response_data = cast(
            JSONObject,
            raw_response_data,
        )

        if not response_data.get("success", False):
            raise VisionClientError(
                response_data.get("error", "Vision service request failed")
            )

        payload = response_data.get("data", {})

        if not isinstance(payload, dict):
            raise VisionClientError("Vision service returned invalid data")

        return payload

    def _path_with_query(
        self,
        path: str,
        params: QueryParams,
    ) -> str:
        filtered = {key: value for key, value in params.items() if value is not None}

        if not filtered:
            return path

        return f"{path}?{parse.urlencode(filtered)}"

    @staticmethod
    def _parse_float(
        value: object,
        *,
        field: str,
    ) -> float:
        if isinstance(value, bool):
            raise VisionClientError(f"Vision service returned invalid {field}")

        if not isinstance(
            value,
            int | float | str,
        ):
            raise VisionClientError(f"Vision service returned invalid {field}")

        try:
            result = float(value)
        except ValueError as exc:
            raise VisionClientError(f"Vision service returned invalid {field}") from exc

        if not math.isfinite(result):
            raise VisionClientError(f"Vision service returned invalid {field}")

        return result

    @staticmethod
    def _parse_int(
        value: object,
        *,
        field: str,
    ) -> int:
        if isinstance(value, bool):
            raise VisionClientError(f"Vision service returned invalid {field}")

        if not isinstance(
            value,
            int | float | str,
        ):
            raise VisionClientError(f"Vision service returned invalid {field}")

        if isinstance(value, float) and not value.is_integer():
            raise VisionClientError(f"Vision service returned invalid {field}")

        try:
            return int(value)
        except ValueError as exc:
            raise VisionClientError(f"Vision service returned invalid {field}") from exc

    @staticmethod
    def _parse_bool(
        value: object,
        *,
        field: str,
    ) -> bool:
        if not isinstance(value, bool):
            raise VisionClientError(f"Vision service returned invalid {field}")

        return value

    @staticmethod
    def _parse_string(
        value: object,
        *,
        field: str,
        allow_empty: bool = False,
    ) -> str:
        if not isinstance(value, str):
            raise VisionClientError(f"Vision service returned invalid {field}")

        result = value.strip()

        if not result and not allow_empty:
            raise VisionClientError(f"Vision service returned invalid {field}")

        return result

    def _parse_detection(
        self,
        data: JSONObject,
    ) -> ClientDetection:
        label = self._parse_string(
            data.get("label"),
            field="detection label",
        )
        box_data = data.get("box")
        center_data = data.get("center")

        box: tuple[int, int, int, int] | None = None
        center: tuple[int, int] | None = None

        if box_data is not None:
            if not isinstance(box_data, (list, tuple)) or len(box_data) != 4:
                raise VisionClientError(
                    "Vision service returned an invalid detection box"
                )

            try:
                box = (
                    self._parse_int(
                        box_data[0],
                        field="detection box x",
                    ),
                    self._parse_int(
                        box_data[1],
                        field="detection box y",
                    ),
                    self._parse_int(
                        box_data[2],
                        field="detection box width",
                    ),
                    self._parse_int(
                        box_data[3],
                        field="detection box height",
                    ),
                )
            except (TypeError, ValueError) as exc:
                raise VisionClientError(
                    "Vision service returned an invalid detection box"
                ) from exc

        if center_data is not None:
            if not isinstance(center_data, (list, tuple)) or len(center_data) != 2:
                raise VisionClientError(
                    "Vision service returned an invalid detection center"
                )

            try:
                center = (
                    self._parse_int(
                        center_data[0],
                        field="detection center x",
                    ),
                    self._parse_int(
                        center_data[1],
                        field="detection center y",
                    ),
                )
            except (TypeError, ValueError) as exc:
                raise VisionClientError(
                    "Vision service returned an invalid detection center"
                ) from exc

        confidence_value = data.get("confidence")

        confidence = (
            None
            if confidence_value is None
            else self._parse_float(
                confidence_value,
                field="detection confidence",
            )
        )

        extra_data = data.get("data", {})

        return ClientDetection(
            label=label,
            confidence=confidence,
            box=box,
            center=center,
            data=extra_data if isinstance(extra_data, dict) else {},
        )

    def _parse_metadata(
        self,
        data: JSONObject,
    ) -> ClientMetadata:
        detections_data = data.get("detections", [])

        if not isinstance(detections_data, (list, tuple)):
            detections_data = []

        detections = [
            self._parse_detection(item)
            for item in detections_data
            if isinstance(item, dict)
        ]

        extra_data = data.get("data", {})

        source = self._parse_string(
            data.get("source"),
            field="metadata source",
        )

        return ClientMetadata(
            source=source,
            timestamp=self._parse_float(
                data.get("timestamp", 0.0),
                field="metadata timestamp",
            ),
            detections=detections,
            data=extra_data if isinstance(extra_data, dict) else {},
        )

    def _parse_detection_status(
        self,
        data: JSONObject,
    ) -> ClientDetectionStatus:
        detectors_data = data.get("detectors", {})
        enabled_data = data.get("enabled", {})
        disabled_data = data.get("disabled")

        detectors: dict[str, bool]

        if isinstance(detectors_data, dict):
            # Enable/disable endpoints return the state map directly.
            detectors = {
                str(name): self._parse_bool(
                    enabled,
                    field=f"{name} detector state",
                )
                for name, enabled in detectors_data.items()
            }

        elif isinstance(detectors_data, list):
            state_map = enabled_data if isinstance(enabled_data, dict) else {}

            detectors = {}

            for detector_name_value in detectors_data:
                detector_name = self._parse_string(
                    detector_name_value,
                    field="detector name",
                )

                detectors[detector_name] = self._parse_bool(
                    state_map.get(
                        detector_name,
                        False,
                    ),
                    field=f"{detector_name} detector state",
                )

        else:
            raise VisionClientError("Vision service returned invalid detector status")

        changed: str | None = None

        if isinstance(enabled_data, str):
            changed = enabled_data
        elif isinstance(disabled_data, str):
            changed = disabled_data

        return ClientDetectionStatus(
            detectors=detectors,
            changed=changed,
        )

    def _parse_stream_overlay_status(
        self,
        data: JSONObject,
    ) -> ClientStreamOverlayStatus:
        source = data.get("source")

        return ClientStreamOverlayStatus(
            enabled=self._parse_bool(
                data.get(
                    "enabled",
                    False,
                ),
                field="stream overlay enabled state",
            ),
            source=(
                self._parse_string(
                    source,
                    field="stream overlay source",
                )
                if source is not None
                else None
            ),
        )

    def _parse_camera_statistics(
        self,
        data: JSONObject,
    ) -> ClientCameraStatistics:
        last_error = data.get("last_error")

        return ClientCameraStatistics(
            running=self._parse_bool(
                data.get(
                    "running",
                    False,
                ),
                field="camera running state",
            ),
            fps=self._parse_float(
                data.get("fps", 0.0),
                field="camera FPS",
            ),
            consumer_count=self._parse_int(
                data.get("consumer_count", 0),
                field="camera consumer count",
            ),
            has_frame=self._parse_bool(
                data.get(
                    "has_frame",
                    False,
                ),
                field="camera frame state",
            ),
            last_error=(str(last_error) if last_error is not None else None),
        )

    def _parse_streaming_statistics(
        self,
        data: JSONObject,
    ) -> ClientStreamingStatistics:
        overlay_data = data.get("overlay", {})

        if not isinstance(overlay_data, dict):
            overlay_data = {}

        return ClientStreamingStatistics(
            running=self._parse_bool(
                data.get(
                    "running",
                    False,
                ),
                field="streaming running state",
            ),
            clients=self._parse_int(
                data.get("clients", 0),
                field="streaming client count",
            ),
            frames_received=self._parse_int(
                data.get("frames_received", 0),
                field="streaming frame count",
            ),
            has_frame=self._parse_bool(
                data.get(
                    "has_frame",
                    False,
                ),
                field="streaming frame state",
            ),
            overlay=self._parse_stream_overlay_status(overlay_data),
        )

    def _parse_recording_status(
        self,
        data: JSONObject,
    ) -> ClientRecordingStatus:
        overlay_data = data.get("overlay", {})

        if not isinstance(overlay_data, dict):
            overlay_data = {}

        return ClientRecordingStatus(
            active=self._parse_bool(
                data.get(
                    "active",
                    False,
                ),
                field="recording active state",
            ),
            overlay=self._parse_stream_overlay_status(overlay_data),
        )

    def _parse_detection_statistics(
        self,
        data: JSONObject,
    ) -> ClientDetectionStatistics:
        detectors_data = data.get("detectors", {})
        metadata_sources_data = data.get("metadata_sources", [])

        detectors: dict[str, bool] = {}

        if isinstance(detectors_data, dict):
            detectors = {
                str(name): self._parse_bool(
                    enabled,
                    field=f"{name} detector state",
                )
                for name, enabled in detectors_data.items()
            }

        metadata_sources: list[str] = []

        if isinstance(metadata_sources_data, list):
            metadata_sources = [
                self._parse_string(
                    source,
                    field="metadata source",
                )
                for source in metadata_sources_data
            ]

        return ClientDetectionStatistics(
            detectors=detectors,
            metadata_sources=metadata_sources,
        )

    def _parse_server_statistics(
        self,
        data: JSONObject,
    ) -> ClientVisionServerStatistics:
        return ClientVisionServerStatistics(
            host=self._parse_string(
                data.get("host"),
                field="server host",
            ),
            port=self._parse_int(
                data.get("port", 0),
                field="server port",
            ),
            fps=self._parse_float(
                data.get("fps", 0.0),
                field="server FPS",
            ),
        )

    def _parse_statistics(
        self,
        data: JSONObject,
    ) -> ClientVisionStatistics:
        camera_data = data.get("camera", {})
        streaming_data = data.get("streaming", {})
        recording_data = data.get("recording", {})
        detection_data = data.get("detection", {})
        server_data = data.get("server", {})

        if not isinstance(camera_data, dict):
            camera_data = {}

        if not isinstance(streaming_data, dict):
            streaming_data = {}

        if not isinstance(recording_data, dict):
            recording_data = {}

        if not isinstance(detection_data, dict):
            detection_data = {}

        if not isinstance(server_data, dict):
            server_data = {}

        return ClientVisionStatistics(
            running=self._parse_bool(
                data.get(
                    "running",
                    False,
                ),
                field="Vision running state",
            ),
            camera=self._parse_camera_statistics(camera_data),
            streaming=self._parse_streaming_statistics(streaming_data),
            recording=self._parse_recording_status(recording_data),
            detection=self._parse_detection_statistics(detection_data),
            server=self._parse_server_statistics(server_data),
        )
