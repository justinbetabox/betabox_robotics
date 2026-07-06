from aiohttp import web

from betabox_robotics.vision.webrtc import WebRTCStreamer

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <title>Betabox Vision WebRTC Test</title>
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
  <h1>Betabox Vision WebRTC Test</h1>
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


class WebRTCSignalingServer:
    """
    Minimal local WebRTC signaling server.

    This is for local testing and classroom LAN use. It does not own the
    camera. It only connects browser offers to WebRTCStreamer.
    """

    def __init__(
        self,
        streamer: WebRTCStreamer,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        self.streamer = streamer
        self.host = host
        self.port = int(port)
        self.app = web.Application()

        self.app.router.add_get("/", self.index)
        self.app.router.add_post("/offer", self.offer)
        self.app.router.add_get("/stats", self.stats)

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
        return web.json_response(self.streamer.statistics())

    def run(self, *, handle_signals: bool = True) -> None:
        web.run_app(
            self.app,
            host=self.host,
            port=self.port,
            handle_signals=handle_signals,
        )
