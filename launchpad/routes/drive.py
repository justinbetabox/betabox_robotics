from __future__ import annotations

import json
from html import escape
from uuid import uuid4

from aiohttp import WSMsgType, web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.launchpad.drive_controller import (
    ControlState,
    DriveControlError,
    ManualDriveController,
)

def parse_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if isinstance(value, bool):
        return value

    raise DriveControlError(
        f"{name} must be a boolean"
    )

async def drive_page(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    vision_url = escape(
        config.network.vision_url
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>Manual Drive · Betabox Launchpad</title>

    <link
        rel="stylesheet"
        href="/static/launchpad.css"
    >
    <link
        rel="stylesheet"
        href="/static/drive.css"
    >
</head>

<body class="drive-body">
    <header class="drive-header">
        <a class="back-link" href="/">
            ← Launchpad
        </a>

        <div>
            <p class="eyebrow">Robot Control</p>
            <h1>Manual Drive</h1>
        </div>

        <div
            id="drive-connection"
            class="drive-connection status-connecting"
        >
            Connecting…
        </div>
    </header>

    <main class="drive-layout">
        <section class="video-panel">
            <iframe
                class="drive-video"
                src="{vision_url}"
                title="Betabox live camera"
                allow="autoplay"
            ></iframe>

            <div class="video-overlay">
                <span id="drive-owner">
                    Waiting for control…
                </span>

                <span id="drive-command">
                    Stopped
                </span>
            </div>
        </section>

        <section class="control-panel">
            <div class="speed-control">
                <div>
                    <p class="eyebrow">Drive Speed</p>
                    <strong id="speed-value">40%</strong>
                </div>

                <input
                    id="speed"
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value="40"
                    aria-label="Drive speed"
                >
            </div>

            <div class="joystick-section">
                <div>
                    <p class="eyebrow">Drive Control</p>
                    <p class="joystick-help">
                        Drag in any direction to drive and steer.
                    </p>
                </div>

                <div
                    id="drive-joystick"
                    class="joystick"
                    role="application"
                    aria-label="Two-axis drive joystick"
                    tabindex="0"
                >
                    <div class="joystick-crosshair" aria-hidden="true"></div>

                    <div
                        id="drive-stick"
                        class="joystick-stick"
                        aria-hidden="true"
                    ></div>

                    <span class="joystick-label joystick-forward">
                        Forward
                    </span>

                    <span class="joystick-label joystick-reverse">
                        Reverse
                    </span>

                    <span class="joystick-label joystick-left">
                        Left
                    </span>

                    <span class="joystick-label joystick-right">
                        Right
                    </span>
                </div>

                <div class="joystick-readout">
                    <span>
                        Throttle
                        <strong id="throttle-value">0%</strong>
                    </span>

                    <span>
                        Steering
                        <strong id="steering-value">Center</strong>
                    </span>
                </div>
            </div>

            <button
                id="emergency-stop"
                class="emergency-stop"
                type="button"
            >
                <span class="stop-icon">■</span>
                Emergency Stop
            </button>

            <div class="keyboard-help">
                <strong>Keyboard</strong>
                <span>W / ↑ Forward</span>
                <span>S / ↓ Reverse</span>
                <span>A / ← Left</span>
                <span>D / → Right</span>
                <span>Space Stop</span>
            </div>

            <p class="drive-safety">
                The robot stops automatically if this page disconnects
                or stops sending control heartbeats.
            </p>
        </section>
    </main>

    <script src="/static/drive.js"></script>
</body>
</html>
"""

    return web.Response(
        text=html,
        content_type="text/html",
    )


async def drive_websocket(
    request: web.Request,
) -> web.WebSocketResponse:
    controller: ManualDriveController = request.app[
        "drive_controller"
    ]

    websocket = web.WebSocketResponse(
        heartbeat=10.0,
        receive_timeout=15.0,
    )

    await websocket.prepare(request)

    client_id = uuid4().hex

    try:
        claimed = await controller.claim(
            client_id
        )

        if not claimed:
            await websocket.send_json(
                {
                    "type": "busy",
                    "message": (
                        "The robot is already being controlled "
                        "from another browser."
                    ),
                }
            )

            await websocket.close(
                code=4001,
                message=b"drive control busy",
            )

            return websocket

        await websocket.send_json(
            {
                "type": "ready",
                "client_id": client_id,
                "heartbeat_timeout": (
                    controller.heartbeat_timeout
                ),
            }
        )

        async for message in websocket:
            if message.type == WSMsgType.TEXT:
                await handle_drive_message(
                    websocket,
                    controller,
                    client_id,
                    message.data,
                )

            elif message.type == WSMsgType.ERROR:
                break

    finally:
        await controller.release(
            client_id
        )

    return websocket


async def handle_drive_message(
    websocket: web.WebSocketResponse,
    controller: ManualDriveController,
    client_id: str,
    raw_message: str,
) -> None:
    try:
        data = json.loads(raw_message)

        if not isinstance(data, dict):
            raise DriveControlError(
                "message must be a JSON object"
            )

        message_type = data.get("type")

        if message_type == "heartbeat":
            await controller.heartbeat(
                client_id
            )

            await websocket.send_json(
                {
                    "type": "heartbeat",
                }
            )
            return

        if message_type == "stop":
            await controller.emergency_stop(
                client_id
            )

            await websocket.send_json(
                {
                    "type": "stopped",
                }
            )
            return

        if message_type != "control":
            raise DriveControlError(
                "unknown manual-control message type"
            )

        state = ControlState(
            throttle=float(
                data.get("throttle", 0.0)
            ),
            steering=float(
                data.get("steering", 0.0)
            ),
            camera_pan=float(
                data.get("camera_pan", 0.0)
            ),
            camera_tilt=float(
                data.get("camera_tilt", 0.0)
            ),
            headlights=parse_bool(
                data.get("headlights", False),
                name="headlights",
            ),
            horn=parse_bool(
                data.get("horn", False),
                name="horn",
            ),
        )

        await controller.update_state(
            client_id,
            state,
        )

        await websocket.send_json(
            {
                "type": "accepted",
                "state": {
                    "throttle": state.throttle,
                    "steering": state.steering,
                    "camera_pan": state.camera_pan,
                    "camera_tilt": state.camera_tilt,
                    "headlights": state.headlights,
                    "horn": state.horn,
                },
            }
        )

    except (
        DriveControlError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        await websocket.send_json(
            {
                "type": "error",
                "message": str(exc),
            }
        )


def setup_drive_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/drive",
        drive_page,
    )

    app.router.add_get(
        "/ws/drive",
        drive_websocket,
    )
