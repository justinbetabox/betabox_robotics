from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib import error, parse, request

if TYPE_CHECKING:
    from betabox_robotics.robots.config import VisionConfig

class VisionClientError(Exception):
    """Raised when the managed Vision service cannot complete a request."""


@dataclass(frozen=True)
class ClientSnapshot:
    path: Path
    timestamp: float
    format: str


@dataclass(frozen=True)
class ClientRecording:
    path: Path
    start_timestamp: float
    end_timestamp: float
    frame_count: int
    fps: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_timestamp - self.start_timestamp)


@dataclass(frozen=True)
class ClientDetection:
    label: str
    confidence: float | None
    box: tuple[int, int, int, int] | None
    center: tuple[int, int] | None
    data: dict[str, Any]


@dataclass(frozen=True)
class ClientMetadata:
    source: str
    timestamp: float
    detections: list[ClientDetection]
    data: dict[str, Any]


@dataclass(frozen=True)
class ClientDetectionStatus:
    detectors: dict[str, bool]
    changed: str | None = None

    @property
    def enabled(self) -> list[str]:
        return sorted(
            name
            for name, is_enabled in self.detectors.items()
            if is_enabled
        )

    @property
    def disabled(self) -> list[str]:
        return sorted(
            name
            for name, is_enabled in self.detectors.items()
            if not is_enabled
        )

    def is_enabled(self, name: str) -> bool:
        return bool(self.detectors.get(name, False))


@dataclass(frozen=True)
class ClientStreamOverlayStatus:
    enabled: bool
    source: str | None = None


@dataclass(frozen=True)
class ClientCameraStatistics:
    running: bool
    fps: float
    consumer_count: int
    has_frame: bool
    last_error: str | None


@dataclass(frozen=True)
class ClientStreamingStatistics:
    running: bool
    clients: int
    frames_received: int
    has_frame: bool
    overlay: ClientStreamOverlayStatus


@dataclass(frozen=True)
class ClientRecordingStatus:
    active: bool
    overlay: ClientStreamOverlayStatus


@dataclass(frozen=True)
class ClientDetectionStatistics:
    detectors: dict[str, bool]
    metadata_sources: list[str]


@dataclass(frozen=True)
class ClientVisionServerStatistics:
    host: str
    port: int
    fps: float


@dataclass(frozen=True)
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
            raise VisionClientError(
                "timeout must be greater than 0"
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)

    @classmethod
    def default(
        cls,
        config: "VisionConfig",
    ) -> "VisionClient":
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
        path = self._path_with_query(
            "/snapshot",
            {
                "filename": filename,
                "overlay": "true" if overlay else None,
                "source": source,
            },
        )
        data = self._post(path)

        return ClientSnapshot(
            path=Path(data["path"]),
            timestamp=float(data["timestamp"]),
            format=str(data["format"]),
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
        data = self._post(path)
        return Path(data["path"])

    def stop_recording(self) -> ClientRecording:
        data = self._post("/recording/stop")

        return ClientRecording(
            path=Path(data["path"]),
            start_timestamp=float(data["start_timestamp"]),
            end_timestamp=float(data["end_timestamp"]),
            frame_count=int(data["frame_count"]),
            fps=float(data["fps"]),
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
        filtered = {
            key: value
            for key, value in params.items()
            if value is not None
        }

        if not filtered:
            return path

        return f"{path}?{parse.urlencode(filtered)}"

    def _parse_detection(
        self,
        data: dict[str, Any],
    ) -> ClientDetection:
        box_data = data.get("box")
        center_data = data.get("center")

        box: tuple[int, int, int, int] | None = None
        center: tuple[int, int] | None = None

        if isinstance(box_data, (list, tuple)) and len(box_data) == 4:
            box = (
                int(box_data[0]),
                int(box_data[1]),
                int(box_data[2]),
                int(box_data[3]),
            )

        if isinstance(center_data, (list, tuple)) and len(center_data) == 2:
            center = (
                int(center_data[0]),
                int(center_data[1]),
            )

        confidence_value = data.get("confidence")
        confidence = (
            float(confidence_value)
            if confidence_value is not None
            else None
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

        detections = [
            self._parse_detection(item)
            for item in detections_data
            if isinstance(item, dict)
        ]

        extra_data = data.get("data", {})

        return ClientMetadata(
            source=str(data.get("source", "")),
            timestamp=float(data.get("timestamp", 0.0)),
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
                str(name): bool(enabled)
                for name, enabled in detectors_data.items()
            }

        elif isinstance(detectors_data, list):
            # GET /detection returns detector names plus a separate
            # enabled-state mapping.
            state_map = (
                enabled_data
                if isinstance(enabled_data, dict)
                else {}
            )

            detectors = {
                str(name): bool(state_map.get(name, False))
                for name in detectors_data
            }

        else:
            raise VisionClientError(
                "Vision service returned invalid detector status"
            )

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
            fps=float(data.get("fps", 0.0)),
            consumer_count=int(data.get("consumer_count", 0)),
            has_frame=bool(data.get("has_frame", False)),
            last_error=str(last_error) if last_error is not None else None,
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
            clients=int(data.get("clients", 0)),
            frames_received=int(data.get("frames_received", 0)),
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
                str(name): bool(enabled)
                for name, enabled in detectors_data.items()
            }

        metadata_sources: list[str] = []

        if isinstance(metadata_sources_data, list):
            metadata_sources = [
                str(source)
                for source in metadata_sources_data
            ]

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
            port=int(data.get("port", 0)),
            fps=float(data.get("fps", 0.0)),
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
