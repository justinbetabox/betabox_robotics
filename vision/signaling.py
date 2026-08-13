from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TypeAlias, cast

from aiohttp import web
from aiohttp.typedefs import Handler

from betabox_robotics.vision.detection import DetectionError
from betabox_robotics.vision.detectors.color import HSVRangeInput
from betabox_robotics.vision.frame_source import FrameSourceError
from betabox_robotics.vision.interfaces import (
    VisionServiceInterface,
)
from betabox_robotics.vision.overlay import OverlayError
from betabox_robotics.vision.recording import RecordingError
from betabox_robotics.vision.snapshot import (
    SnapshotError,
    normalize_image_format,
)
from betabox_robotics.vision.stream import StreamError
from betabox_robotics.vision.webrtc import WebRTCStreamer

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

HANDLED_ERRORS = (
    TypeError,
    ValueError,
    DetectionError,
    FrameSourceError,
    OverlayError,
    RecordingError,
    SnapshotError,
    StreamError,
)

_TRUE_VALUES = frozenset(
    {
        "1",
        "true",
        "yes",
        "on",
    }
)

_FALSE_VALUES = frozenset(
    {
        "0",
        "false",
        "no",
        "off",
    }
)

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <title>Betabox Vision</title>
  <style>
    body {
      font-family: sans-serif;
      background: #111;
      color: #eee;
      text-align: center;
    }
    video {
      width: 640px;
      max-width: 95vw;
      background: #000;
      border: 1px solid #555;
    }
    button {
      margin: 1rem;
      padding: 0.5rem 1rem;
      font-size: 1rem;
    }
    pre {
      text-align: left;
      display: inline-block;
      background: #222;
      padding: 1rem;
      max-width: 95vw;
      overflow: auto;
    }
  </style>
</head>
<body>
  <h1>Betabox Vision</h1>
  <video id="video" autoplay playsinline muted></video>
  <br>
  <button onclick="start()">Start</button>
  <pre id="log"></pre>

  <script>
    const log = (msg) => {
      document.getElementById("log").textContent += msg + "\\n";
    };

    async function start() {
      let pc = null;

      try {
        pc = new RTCPeerConnection();

        pc.ontrack = (event) => {
          log("Received track");
          document.getElementById("video").srcObject = event.streams[0];
        };

        pc.onconnectionstatechange = () => {
          log("Connection state: " + pc.connectionState);

          if (pc.connectionState === "closed") {
              log("Connection closed");
          }
        };

        pc.addTransceiver("video", { direction: "recvonly" });

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch("/offer", {
          method: "POST",
          body: JSON.stringify({
            sdp: pc.localDescription.sdp,
            type: pc.localDescription.type
          }),
          headers: {
            "Content-Type": "application/json"
          }
        });

        const answer = await response.json();

        if (!response.ok) {
          throw new Error(
            answer.error || `WebRTC offer failed with HTTP ${response.status}`
          );
        }

        await pc.setRemoteDescription(answer);

        log("WebRTC answer applied");
      } catch (error) {
        console.error(error);

        log("Error: " + (error instanceof Error ? error.message : String(error)));

        if (pc !== null) {
          try {
            pc.close();
          } catch {
            // Ignore cleanup failures.
          }
        }
      }
    }
  </script>
</body>
</html>
"""


def _validate_host(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("host must be a string")

    host = value.strip()

    if not host:
        raise ValueError("host cannot be empty")

    return host


def _validate_port(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("port must be an integer")

    if not 1 <= value <= 65535:
        raise ValueError("port must be between 1 and 65535")

    return value


@web.middleware
async def error_middleware(
    request: web.Request,
    handler: Handler,
) -> web.StreamResponse:
    try:
        response: web.StreamResponse = await handler(request)
        return response

    except HANDLED_ERRORS as exc:
        return fail(
            str(exc),
            status=400,
        )


def to_json(
    value: object,
) -> JSONValue:
    if value is None:
        return None

    if isinstance(
        value,
        str | int | float | bool,
    ):
        return value

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value) and not isinstance(
        value,
        type,
    ):
        return to_json(asdict(value))

    if isinstance(value, Mapping):
        mapping = cast(
            Mapping[object, object],
            value,
        )

        return {str(key): to_json(item) for key, item in mapping.items()}

    if isinstance(
        value,
        list | tuple | set,
    ):
        values = cast(
            list[object] | tuple[object, ...] | set[object],
            value,
        )

        return [to_json(item) for item in values]

    raise TypeError(f"value is not JSON serializable: {type(value).__name__}")


def ok(
    data: object = None,
) -> web.Response:
    return web.json_response(
        {
            "success": True,
            "data": to_json(data) if data is not None else {},
        }
    )


def fail(
    message: str,
    *,
    status: int = 400,
) -> web.Response:
    return web.json_response(
        {
            "success": False,
            "error": message,
        },
        status=status,
    )


def query_bool(
    request: web.Request,
    name: str,
    *,
    default: bool = False,
) -> bool:
    value = request.query.get(name)

    if value is None:
        return default

    normalized = value.strip().casefold()

    if normalized in _TRUE_VALUES:
        return True

    if normalized in _FALSE_VALUES:
        return False

    raise ValueError(f"{name} must be a boolean")


async def json_object(
    request: web.Request,
) -> dict[str, JSONValue]:
    try:
        raw_data = cast(
            object,
            await request.json(),
        )
    except (
        UnicodeDecodeError,
        ValueError,
        web.HTTPException,
    ) as exc:
        raise ValueError("request body must contain valid JSON") from exc

    if not isinstance(raw_data, dict):
        raise TypeError("request JSON must be an object")

    data = cast(
        dict[str, JSONValue],
        raw_data,
    )

    return data


def required_string(
    data: dict[str, JSONValue],
    name: str,
) -> str:
    value = data.get(name)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")

    return value.strip()


def optional_string_sequence(
    value: JSONValue,
    *,
    name: str,
) -> str | list[str] | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        values: list[str] = []

        for item in value:
            if not isinstance(item, str):
                raise TypeError(f"{name} must contain only strings")

            values.append(item)

        return values

    raise ValueError(f"{name} must be a string or array of strings")


def hsv_value(
    value: JSONValue,
    *,
    name: str,
) -> tuple[int, int, int]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must contain three integers")

    components: list[int] = []

    for component in value:
        if isinstance(component, bool) or not isinstance(
            component,
            int,
        ):
            raise TypeError(f"{name} must contain three integers")

        components.append(component)

    return (
        components[0],
        components[1],
        components[2],
    )


def hsv_range(
    value: JSONValue,
    *,
    name: str,
) -> HSVRangeInput:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be an HSV range")

    # Single range:
    # [[h, s, v], [h, s, v]]
    if len(value) == 2:
        try:
            lower = hsv_value(
                value[0],
                name=f"{name} lower",
            )
            upper = hsv_value(
                value[1],
                name=f"{name} upper",
            )
        except ValueError:
            pass
        else:
            return (
                lower,
                upper,
            )

    # Sequence of ranges:
    # [
    #   [[h, s, v], [h, s, v]],
    #   [[h, s, v], [h, s, v]],
    # ]
    ranges: list[
        tuple[
            tuple[int, int, int],
            tuple[int, int, int],
        ]
    ] = []

    for index, item in enumerate(value):
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError(f"{name}[{index}] must be an HSV range")

        ranges.append(
            (
                hsv_value(
                    item[0],
                    name=f"{name}[{index}] lower",
                ),
                hsv_value(
                    item[1],
                    name=f"{name}[{index}] upper",
                ),
            )
        )

    if not ranges:
        raise ValueError(f"{name} must contain at least one HSV range")

    return ranges


def optional_custom_ranges(
    value: JSONValue,
) -> dict[str, HSVRangeInput] | None:
    if value is None:
        return None

    if not isinstance(value, dict):
        raise TypeError("custom_ranges must be an object")

    result: dict[str, HSVRangeInput] = {}

    for name, raw_range in value.items():
        result[name] = hsv_range(
            raw_range,
            name=f"custom_ranges.{name}",
        )

    return result


class WebRTCSignalingServer:
    """
    Minimal local WebRTC signaling server.

    This is for local testing and classroom LAN use. It does not own the
    camera. It only connects browser offers to WebRTCStreamer.
    """

    vision: VisionServiceInterface
    streamer: WebRTCStreamer
    host: str
    port: int
    app: web.Application

    def __init__(
        self,
        vision: VisionServiceInterface,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        if not hasattr(
            vision,
            "streamer",
        ):
            raise TypeError("vision must provide a streamer")

        self.vision = vision
        self.streamer = vision.streamer
        self.host = _validate_host(host)
        self.port = _validate_port(port)
        self.app = web.Application(
            middlewares=[
                error_middleware,
            ]
        )
        self.app.on_shutdown.append(self.on_shutdown)

        _ = self.app.router.add_get(
            "/",
            self.index,
        )
        _ = self.app.router.add_post(
            "/offer",
            self.offer,
        )
        _ = self.app.router.add_get(
            "/stats",
            self.stats,
        )
        _ = self.app.router.add_post(
            "/snapshot",
            self.snapshot,
        )
        _ = self.app.router.add_post(
            "/recording/start",
            self.recording_start,
        )
        _ = self.app.router.add_post(
            "/recording/stop",
            self.recording_stop,
        )
        _ = self.app.router.add_get(
            "/metadata",
            self.metadata,
        )
        _ = self.app.router.add_get(
            "/detection",
            self.detection_status,
        )
        _ = self.app.router.add_post(
            "/detection/enable",
            self.detection_enable,
        )
        _ = self.app.router.add_post(
            "/detection/disable",
            self.detection_disable,
        )
        _ = self.app.router.add_post(
            "/detection/color/enable",
            self.color_detection_enable,
        )
        _ = self.app.router.add_post(
            "/stream/overlay/enable",
            self.stream_overlay_enable,
        )
        _ = self.app.router.add_post(
            "/stream/overlay/disable",
            self.stream_overlay_disable,
        )

    async def index(
        self,
        _request: web.Request,
    ) -> web.Response:
        return web.Response(text=INDEX_HTML, content_type="text/html")

    async def offer(
        self,
        request: web.Request,
    ) -> web.Response:
        params = await json_object(request)

        sdp = required_string(
            params,
            "sdp",
        )
        offer_type = required_string(
            params,
            "type",
        )

        answer = await self.streamer.offer(
            sdp=sdp,
            offer_type=offer_type,
        )

        return web.json_response(answer)

    async def stats(
        self,
        _request: web.Request,
    ) -> web.Response:
        return ok(self.vision.statistics())

    async def snapshot(
        self,
        request: web.Request,
    ) -> web.Response:
        overlay = query_bool(
            request,
            "overlay",
        )

        source = request.query.get("source")
        image_format = normalize_image_format(
            request.query.get(
                "format",
                "jpg",
            )
        )

        snapshot = self.vision.capture_snapshot_data(
            overlay=overlay,
            source=source,
            image_format=image_format,
        )

        content_type = "image/png" if snapshot.format == "png" else "image/jpeg"

        return web.Response(
            body=snapshot.data,
            content_type=content_type,
            headers={
                "X-Betabox-Timestamp": str(snapshot.timestamp),
                "X-Betabox-Format": snapshot.format,
            },
        )

    async def recording_start(
        self,
        request: web.Request,
    ) -> web.Response:
        overlay = query_bool(
            request,
            "overlay",
        )
        source = request.query.get("source")
        filename = request.query.get("filename")

        path = self.vision.start_recording(
            filename=filename,
            overlay=overlay,
            source=source,
        )

        return ok(
            {
                "recording": True,
                "path": path,
            }
        )

    async def recording_stop(
        self,
        _request: web.Request,
    ) -> web.Response:
        recording = self.vision.stop_recording_data()

        return web.Response(
            body=recording.data,
            content_type="video/mp4",
            headers={
                "X-Betabox-Format": recording.format,
                "X-Betabox-Start-Timestamp": str(recording.start_timestamp),
                "X-Betabox-End-Timestamp": str(recording.end_timestamp),
                "X-Betabox-Frame-Count": str(recording.frame_count),
                "X-Betabox-FPS": str(recording.fps),
            },
        )

    async def metadata(
        self,
        request: web.Request,
    ) -> web.Response:
        source = request.query.get("source")
        metadata = self.vision.latest_metadata(source)
        return ok(metadata or {})

    async def detection_status(
        self,
        _request: web.Request,
    ) -> web.Response:
        return ok(
            {
                "detectors": self.vision.detection_names(),
                "enabled": self.vision.detection_status(),
            }
        )

    async def detection_enable(
        self,
        request: web.Request,
    ) -> web.Response:
        params = await json_object(request)
        name = required_string(params, "name")

        self.vision.enable_detection(name)

        return ok(
            {
                "enabled": name,
                "detectors": self.vision.detection_status(),
            }
        )

    async def detection_disable(
        self,
        request: web.Request,
    ) -> web.Response:

        params = await json_object(request)
        name = required_string(params, "name")
        self.vision.disable_detection(name)
        return ok(
            {
                "disabled": name,
                "detectors": self.vision.detection_status(),
            }
        )

    async def color_detection_enable(
        self,
        request: web.Request,
    ) -> web.Response:
        params = await json_object(request)

        colors = optional_string_sequence(
            params.get("colors"),
            name="colors",
        )

        custom_ranges = optional_custom_ranges(
            params.get("custom_ranges"),
        )

        min_area_value = params.get("min_area")

        if min_area_value is None:
            min_area = None
        elif isinstance(min_area_value, bool) or not isinstance(
            min_area_value,
            int | float,
        ):
            raise ValueError("min_area must be a number")
        else:
            min_area = float(min_area_value)

        self.vision.enable_color_detection(
            colors,
            custom_ranges=custom_ranges,
            min_area=min_area,
        )

        return ok(
            {
                "enabled": "color",
                "detectors": self.vision.detection_status(),
            }
        )

    async def stream_overlay_enable(
        self,
        request: web.Request,
    ) -> web.Response:
        params = await json_object(request)
        source = params.get("source")

        if source is not None and not isinstance(source, str):
            raise ValueError("source must be a string")

        self.vision.enable_stream_overlay(source)

        return ok(self.vision.stream_overlay_status())

    async def stream_overlay_disable(
        self,
        _request: web.Request,
    ) -> web.Response:
        self.vision.disable_stream_overlay()
        return ok(self.vision.stream_overlay_status())

    async def on_shutdown(self, _app: web.Application) -> None:
        await self.streamer.close_peers()

    def run(self, *, handle_signals: bool = True) -> None:
        web.run_app(
            self.app,
            host=self.host,
            port=self.port,
            handle_signals=handle_signals,
        )
