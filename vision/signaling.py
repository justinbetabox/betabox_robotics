from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from betabox_robotics.vision.service import VisionService

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
      const pc = new RTCPeerConnection();

      pc.ontrack = (event) => {
        log("Received track");
        document.getElementById("video").srcObject = event.streams[0];
      };

      pc.onconnectionstatechange = () => {
        log("Connection state: " + pc.connectionState);
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
      await pc.setRemoteDescription(answer);

      log("WebRTC answer applied");
    }
  </script>
</body>
</html>
"""

def to_json(value: Any) -> Any:
    if value is None:
        return None

    if is_dataclass(value) and not isinstance(value, type):
        return to_json(asdict(value))

    if isinstance(value, dict):
        return {key: to_json(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_json(item) for item in value]

    if isinstance(value, Path):
        return str(value)

    return value

def ok(data=None):
    return web.json_response(
        {
            "success": True,
            "data": to_json(data) if data is not None else {},
        }
    )

def fail(message: str, *, status: int = 400):
    return web.json_response(
        {
            "success": False,
            "error": message,
        },
        status=status,
    )


class WebRTCSignalingServer:
    """
    Minimal local WebRTC signaling server.

    This is for local testing and classroom LAN use. It does not own the
    camera. It only connects browser offers to WebRTCStreamer.
    """

    def __init__(
        self,
        vision: "VisionService",
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        self.vision = vision
        self.streamer = vision.streamer
        self.host = host
        self.port = int(port)
        self.app = web.Application()

        self.app.router.add_get("/", self.index)
        self.app.router.add_post("/offer", self.offer)
        self.app.router.add_get("/stats", self.stats)
        self.app.router.add_post("/snapshot", self.snapshot)
        self.app.router.add_post("/recording/start", self.recording_start)
        self.app.router.add_post("/recording/stop", self.recording_stop)
        self.app.router.add_get("/metadata", self.metadata)
        self.app.router.add_get("/detection", self.detection_status)
        self.app.router.add_post("/detection/enable", self.detection_enable)
        self.app.router.add_post("/detection/disable", self.detection_disable)
        self.app.router.add_post("/stream/overlay/enable", self.stream_overlay_enable)
        self.app.router.add_post("/stream/overlay/disable", self.stream_overlay_disable)

    async def index(self, request):
        return web.Response(text=INDEX_HTML, content_type="text/html")

    async def offer(self, request):
        params = await request.json()
        answer = await self.streamer.offer(
            sdp=params["sdp"],
            type=params["type"],
        )
        return web.json_response(answer)

    async def stats(self, request):
        return ok(self.vision.statistics())

    async def snapshot(self, request):
        try:
            overlay = request.query.get("overlay", "false").lower() in (
                "1",
                "true",
                "yes",
            )
            source = request.query.get("source")

            snapshot = self.vision.capture_snapshot(
                overlay=overlay,
                source=source,
            )
            return ok(snapshot)
        except Exception as exc:
            return fail(str(exc))

    async def recording_start(self, request):
        try:
            overlay = request.query.get("overlay", "false").lower() in (
                "1",
                "true",
                "yes",
            )
            source = request.query.get("source")

            path = self.vision.start_recording(
                overlay=overlay,
                source=source,
            )

            return ok(
                {
                    "recording": True,
                    "path": str(path),
                }
            )
        except Exception as exc:
            return fail(str(exc))

    async def recording_stop(self, request):
        try:
            recording = self.vision.stop_recording()
            return ok(recording)
        except Exception as exc:
            return fail(str(exc))

    async def metadata(self, request):
        try:
            source = request.query.get("source")
            metadata = self.vision.latest_metadata(source)
            return ok(metadata or {})
        except Exception as exc:
            return fail(str(exc))

    async def detection_status(self, request):
        try:
            return ok(
                {
                    "detectors": self.vision.detection_names(),
                    "enabled": self.vision.detection_status(),
                }
            )
        except Exception as exc:
            return fail(str(exc))

    async def detection_enable(self, request):
        try:
            params = await request.json()
            name = params["name"]
            self.vision.enable_detection(name)
            return ok(
                {
                    "enabled": name,
                    "detectors": self.vision.detection_status(),
                }
            )
        except Exception as exc:
            return fail(str(exc))

    async def detection_disable(self, request):
        try:
            params = await request.json()
            name = params["name"]
            self.vision.disable_detection(name)
            return ok(
                {
                    "disabled": name,
                    "detectors": self.vision.detection_status(),
                }
            )
        except Exception as exc:
            return fail(str(exc))

    async def stream_overlay_enable(self, request):
        try:
            params = await request.json()
            source = params.get("source")
            self.vision.enable_stream_overlay(source)
            return ok(self.vision.stream_overlay_status())
        except Exception as exc:
            return fail(str(exc))

    async def stream_overlay_disable(self, request):
        try:
            self.vision.disable_stream_overlay()
            return ok(self.vision.stream_overlay_status())
        except Exception as exc:
            return fail(str(exc))

    def run(self, *, handle_signals: bool = True) -> None:
        web.run_app(
            self.app,
            host=self.host,
            port=self.port,
            handle_signals=handle_signals,
        )
