from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import strftime
from typing import TYPE_CHECKING, Any
from urllib import error, parse, request

if TYPE_CHECKING:
    from betabox_robotics.robots.config import VisionConfig


class VisionClientError(Exception):
    """Raised when the managed Vision service cannot complete a request."""


@dataclass(frozen=True, slots=True)
class ClientSnapshot:
    path: Path
    timestamp: float
    format: str


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
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ClientMetadata:
    source: str
    timestamp: float
    detections: list[ClientDetection]
    data: dict[str, Any]


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
        return bool(self.detectors.get(name, False))


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

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        *,
        timeout: float = 10.0,
    ) -> None:
        if not base_url:
            raise VisionClientError("base_url cannot be empty")

        if timeout <= 0:
            raise VisionClientError("timeout must be greater than 0")

        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self._recording_filename: str | None = None

    @staticmethod
    def _snapshot_format(
        filename: str | None,
    ) -> str:
        if filename is None:
            return "jpg"

        suffix = Path(filename).suffix.lower()

        if suffix in (".jpg", ".jpeg"):
            return "jpg"

        if suffix == ".png":
            return "png"

        if suffix:
            raise VisionClientError("snapshot filename must use .jpg, .jpeg, or .png")

        return "jpg"

    def _request_bytes(
        self,
        method: str,
        path: str,
    ) -> tuple[bytes, Any]:
        url = f"{self.base_url}{path}"

        req = request.Request(
            url,
            method=method,
        )

        try:
            with request.urlopen(
                req,
                timeout=self.timeout,
            ) as response:
                return (
                    response.read(),
                    response.headers,
                )

        except error.HTTPError as exc:
            response_body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            try:
                error_data = json.loads(response_body)
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
                "Betabox Vision service is not "
                "available. Run: sudo systemctl "
                "start betabox-video.service"
            ) from exc

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
                    f"{media_name} filename must be a plain "
                    "filename without directory components"
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
            output_path.write_bytes(data)
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

        returned_format = headers.get(
            "X-Betabox-Format",
            image_format,
        ).lower()

        timestamp_value = headers.get(
            "X-Betabox-Timestamp",
            "0",
        )

        try:
            timestamp = float(timestamp_value)
        except (TypeError, ValueError) as exc:
            raise VisionClientError(
                "Vision service returned an invalid snapshot timestamp"
            ) from exc

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

        self._post(path)

        self._recording_filename = filename

        return self._recording_output_path(filename)

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

        try:
            start_timestamp = float(
                headers.get(
                    "X-Betabox-Start-Timestamp",
                    "0",
                )
            )
            end_timestamp = float(
                headers.get(
                    "X-Betabox-End-Timestamp",
                    "0",
                )
            )
            frame_count = int(
                headers.get(
                    "X-Betabox-Frame-Count",
                    "0",
                )
            )
            fps = float(
                headers.get(
                    "X-Betabox-FPS",
                    "0",
                )
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
        payload: dict[str, Any] = {}

        if colors is not None:
            payload["colors"] = colors if isinstance(colors, str) else list(colors)

        if min_area is not None:
            payload["min_area"] = float(min_area)

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
        payload: dict[str, Any] = {}

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

    def _get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path)

    def _post(self, path: str) -> dict[str, Any]:
        return self._request("POST", path)

    def _post_json(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, data=data)

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = None
        headers = {}

        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(url, data=body, headers=headers, method=method)

        try:
            with request.urlopen(
                req,
                timeout=self.timeout,
            ) as response:
                response_body = response.read().decode("utf-8")

        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8")

            try:
                error_data = json.loads(response_body)
            except json.JSONDecodeError:
                raise VisionClientError(
                    f"Vision service request failed with HTTP {exc.code}"
                ) from exc

            message = error_data.get("error", f"HTTP {exc.code}")
            raise VisionClientError(str(message)) from exc

        except error.URLError as exc:
            raise VisionClientError(
                "Betabox Vision service is not available. "
                "Run: sudo systemctl start betabox-video.service"
            ) from exc

        try:
            response_data = json.loads(response_body) if response_body else {}
        except json.JSONDecodeError as exc:
            raise VisionClientError(
                f"invalid Vision service response: {response_body}"
            ) from exc

        if not isinstance(response_data, dict):
            raise VisionClientError("Vision service returned an unexpected response")

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
        params: dict[str, Any],
    ) -> str:
        filtered = {key: value for key, value in params.items() if value is not None}

        if not filtered:
            return path

        return f"{path}?{parse.urlencode(filtered)}"

    @staticmethod
    def _parse_float(
        value: Any,
        *,
        field: str,
    ) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise VisionClientError(f"Vision service returned invalid {field}") from exc

    @staticmethod
    def _parse_int(
        value: Any,
        *,
        field: str,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise VisionClientError(f"Vision service returned invalid {field}") from exc

    def _parse_detection(
        self,
        data: dict[str, Any],
    ) -> ClientDetection:
        box_data = data.get("box")
        center_data = data.get("center")

        box: tuple[int, int, int, int] | None = None
        center: tuple[int, int] | None = None

        if isinstance(box_data, (list, tuple)) and len(box_data) == 4:
            try:
                box = (
                    int(box_data[0]),
                    int(box_data[1]),
                    int(box_data[2]),
                    int(box_data[3]),
                )
            except (TypeError, ValueError) as exc:
                raise VisionClientError(
                    "Vision service returned an invalid detection box"
                ) from exc

        if isinstance(center_data, (list, tuple)) and len(center_data) == 2:
            try:
                center = (
                    int(center_data[0]),
                    int(center_data[1]),
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
            label=str(data.get("label", "")),
            confidence=confidence,
            box=box,
            center=center,
            data=extra_data if isinstance(extra_data, dict) else {},
        )

    def _parse_metadata(
        self,
        data: dict[str, Any],
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

        return ClientMetadata(
            source=str(data.get("source", "")),
            timestamp=self._parse_float(
                data.get("timestamp", 0.0),
                field="metadata timestamp",
            ),
            detections=detections,
            data=extra_data if isinstance(extra_data, dict) else {},
        )

    def _parse_detection_status(
        self,
        data: dict[str, Any],
    ) -> ClientDetectionStatus:
        detectors_data = data.get("detectors", {})
        enabled_data = data.get("enabled", {})
        disabled_data = data.get("disabled")

        detectors: dict[str, bool]

        if isinstance(detectors_data, dict):
            # Enable/disable endpoints return the state map directly.
            detectors = {
                str(name): bool(enabled) for name, enabled in detectors_data.items()
            }

        elif isinstance(detectors_data, list):
            # GET /detection returns detector names plus a separate
            # enabled-state mapping.
            state_map = enabled_data if isinstance(enabled_data, dict) else {}

            detectors = {
                str(name): bool(state_map.get(name, False)) for name in detectors_data
            }

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
        data: dict[str, Any],
    ) -> ClientStreamOverlayStatus:
        source = data.get("source")

        return ClientStreamOverlayStatus(
            enabled=bool(data.get("enabled", False)),
            source=str(source) if source is not None else None,
        )

    def _parse_camera_statistics(
        self,
        data: dict[str, Any],
    ) -> ClientCameraStatistics:
        last_error = data.get("last_error")

        return ClientCameraStatistics(
            running=bool(data.get("running", False)),
            fps=self._parse_float(
                data.get("fps", 0.0),
                field="camera FPS",
            ),
            consumer_count=self._parse_int(
                data.get("consumer_count", 0),
                field="camera consumer count",
            ),
            has_frame=bool(data.get("has_frame", False)),
            last_error=(str(last_error) if last_error is not None else None),
        )

    def _parse_streaming_statistics(
        self,
        data: dict[str, Any],
    ) -> ClientStreamingStatistics:
        overlay_data = data.get("overlay", {})

        if not isinstance(overlay_data, dict):
            overlay_data = {}

        return ClientStreamingStatistics(
            running=bool(data.get("running", False)),
            clients=self._parse_int(
                data.get("clients", 0),
                field="streaming client count",
            ),
            frames_received=self._parse_int(
                data.get("frames_received", 0),
                field="streaming frame count",
            ),
            has_frame=bool(data.get("has_frame", False)),
            overlay=self._parse_stream_overlay_status(overlay_data),
        )

    def _parse_recording_status(
        self,
        data: dict[str, Any],
    ) -> ClientRecordingStatus:
        overlay_data = data.get("overlay", {})

        if not isinstance(overlay_data, dict):
            overlay_data = {}

        return ClientRecordingStatus(
            active=bool(data.get("active", False)),
            overlay=self._parse_stream_overlay_status(overlay_data),
        )

    def _parse_detection_statistics(
        self,
        data: dict[str, Any],
    ) -> ClientDetectionStatistics:
        detectors_data = data.get("detectors", {})
        metadata_sources_data = data.get("metadata_sources", [])

        detectors: dict[str, bool] = {}

        if isinstance(detectors_data, dict):
            detectors = {
                str(name): bool(enabled) for name, enabled in detectors_data.items()
            }

        metadata_sources: list[str] = []

        if isinstance(metadata_sources_data, list):
            metadata_sources = [str(source) for source in metadata_sources_data]

        return ClientDetectionStatistics(
            detectors=detectors,
            metadata_sources=metadata_sources,
        )

    def _parse_server_statistics(
        self,
        data: dict[str, Any],
    ) -> ClientVisionServerStatistics:
        return ClientVisionServerStatistics(
            host=str(data.get("host", "")),
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
        data: dict[str, Any],
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
            running=bool(data.get("running", False)),
            camera=self._parse_camera_statistics(camera_data),
            streaming=self._parse_streaming_statistics(streaming_data),
            recording=self._parse_recording_status(recording_data),
            detection=self._parse_detection_statistics(detection_data),
            server=self._parse_server_statistics(server_data),
        )
