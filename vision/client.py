from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request
import json


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


class VisionClient:
    """
    Client for the managed Betabox Vision service.

    This does not open the camera. It talks to betabox-video.service.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8080") -> None:
        self.base_url = base_url.rstrip("/")

    def statistics(self) -> dict[str, Any]:
        return self._get("/stats")

    def snapshot(self) -> ClientSnapshot:
        data = self._post("/snapshot")

        return ClientSnapshot(
            path=Path(data["path"]),
            timestamp=float(data["timestamp"]),
            format=str(data["format"]),
        )

    def start_recording(self) -> Path:
        data = self._post("/recording/start")
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

    def metadata(self, source: str | None = None) -> dict[str, Any]:
        path = "/metadata" if source is None else f"/metadata?source={source}"
        return self._get(path)

    def detection_status(self) -> dict[str, Any]:
        return self._get("/detection")

    def enable_detection(self, name: str) -> dict[str, Any]:
        return self._post_json("/detection/enable", {"name": name})

    def disable_detection(self, name: str) -> dict[str, Any]:
        return self._post_json("/detection/disable", {"name": name})

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
            with request.urlopen(req, timeout=10) as response:
                body = response.read().decode("utf-8")
        except error.URLError as exc:
            raise VisionClientError(
                "Betabox Vision service is not available. "
                "Run: sudo systemctl start betabox-video.service"
            ) from exc

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise VisionClientError(f"invalid Vision service response: {body}") from exc

        if not isinstance(data, dict):
            raise VisionClientError("Vision service returned an unexpected response")

        if not data.get("success", False):
            raise VisionClientError(
                data.get("error", "Vision service request failed")
            )

        payload = data.get("data", {})

        if not isinstance(payload, dict):
            raise VisionClientError("Vision service returned invalid data")

        return payload
