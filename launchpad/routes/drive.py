from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import aiohttp
from aiohttp import WSMsgType, web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.launchpad.drive_controller import (
    ControlState,
    DriveControlError,
    ManualDriveController,
)

from betabox_robotics.exceptions import (
    RobotBusyError,
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

    html = """<!doctype html>
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
            <div
                class="video-status"
                aria-live="polite"
            >
                Connecting camera…
            </div>
            <div
                id="drive-hud"
                class="drive-hud"
                aria-live="polite"
            >
                <div class="drive-hud-primary">
                    <span
                        id="hud-health-dot"
                        class="drive-hud-dot hud-unknown"
                    ></span>

                    <div class="drive-hud-value">
                        <span>Robot</span>
                        <strong id="hud-health">
                            Checking…
                        </strong>
                    </div>
                </div>

                <div class="drive-hud-value">
                    <span>Battery</span>
                    <strong id="hud-battery">
                        --
                    </strong>
                </div>

                <div class="drive-hud-value">
                    <span>Temperature</span>
                    <strong id="hud-temperature">
                        --
                    </strong>
                </div>

                <div class="drive-hud-value">
                    <span>Drive</span>
                    <strong id="hud-drive">
                        Connecting
                    </strong>
                </div>

                <div class="drive-hud-value">
                    <span>Camera</span>
                    <strong id="hud-camera">
                        Connecting
                    </strong>
                </div>
            </div>
            <video
                id="drive-video"
                class="drive-video"
                autoplay
                playsinline
                muted
            ></video>

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
            <div class="camera-control-section">
                <div class="camera-control-heading">
                    <div>
                        <p class="eyebrow">Camera Control</p>
                        <p class="joystick-help">
                            Drag to point the camera. It stays in position
                            when released.
                        </p>
                    </div>

                    <button
                        id="camera-center"
                        class="camera-center-button"
                        type="button"
                    >
                        Center Camera
                    </button>
                </div>

                <div
                    id="camera-joystick"
                    class="joystick camera-joystick"
                    role="application"
                    aria-label="Camera pan and tilt joystick"
                    tabindex="0"
                >
                    <div
                        class="joystick-crosshair"
                        aria-hidden="true"
                    ></div>

                    <div
                        id="camera-stick"
                        class="joystick-stick camera-stick"
                        aria-hidden="true"
                    ></div>

                    <span class="joystick-label joystick-forward">
                        Up
                    </span>

                    <span class="joystick-label joystick-reverse">
                        Down
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
                        Pan
                        <strong id="camera-pan-value">Center</strong>
                    </span>

                    <span>
                        Tilt
                        <strong id="camera-tilt-value">Center</strong>
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

    <script
        type="module"
        src="/static/drive.js"
    ></script>
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
        try:
            claimed = await controller.claim(
                client_id
            )

        except RobotBusyError as exc:
            await send_json_if_open(
                websocket,
                {
                    "type": "unavailable",
                    "message": str(exc),
                },
            )

            await websocket.close(
                code=4002,
                message=b"robot hardware unavailable",
            )

            return websocket

        except Exception as exc:
            await send_json_if_open(
                websocket,
                {
                    "type": "error",
                    "message": (
                        "Manual Drive could not start: "
                        f"{exc}"
                    ),
                },
            )

            await websocket.close(
                code=1011,
                message=b"manual drive failed",
            )

            return websocket

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
                if websocket.closed:
                    break

                await handle_drive_message(
                    websocket,
                    controller,
                    client_id,
                    message.data,
                )

            elif message.type in (
                WSMsgType.CLOSE,
                WSMsgType.CLOSING,
                WSMsgType.CLOSED,
                WSMsgType.ERROR,
            ):
                break

    finally:
        await controller.release(
            client_id
        )

    return websocket


async def send_json_if_open(
    websocket: web.WebSocketResponse,
    data: dict,
) -> bool:
    if websocket.closed:
        return False

    try:
        await websocket.send_json(
            data
        )
        return True

    except (
        ConnectionResetError,
        aiohttp.ClientConnectionError,
    ):
        return False

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

            await send_json_if_open(
                websocket,
                {
                    "type": "heartbeat",
                },
            )
            return

        if message_type == "stop":
            await controller.emergency_stop(
                client_id
            )

            await send_json_if_open(
                websocket,
                {
                    "type": "stopped",
                },
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

        return

    except (
        DriveControlError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        await send_json_if_open(
            websocket,
            {
                "type": "error",
                "message": str(exc),
            },
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

    app.router.add_post(
        "/api/vision/offer",
        vision_offer_proxy,
    )

async def vision_offer_proxy(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    try:
        offer = await request.json()

        if not isinstance(offer, dict):
            raise ValueError(
                "offer must be a JSON object"
            )

        sdp = offer.get("sdp")
        offer_type = offer.get("type")

        if not isinstance(sdp, str) or not sdp:
            raise ValueError(
                "offer sdp must be a non-empty string"
            )

        if not isinstance(offer_type, str) or not offer_type:
            raise ValueError(
                "offer type must be a non-empty string"
            )

        vision_url = (
            f"{config.network.vision_url}"
            "/offer"
        )

        timeout = aiohttp.ClientTimeout(
            total=10
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:
            async with session.post(
                vision_url,
                json={
                    "sdp": sdp,
                    "type": offer_type,
                },
            ) as response:
                response_data = await response.json()

                if response.status >= 400:
                    return web.json_response(
                        {
                            "error": (
                                "Vision signaling request failed"
                            ),
                            "details": response_data,
                        },
                        status=response.status,
                    )

        return web.json_response(
            response_data
        )

    except (
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        return web.json_response(
            {
                "error": str(exc),
            },
            status=400,
        )

    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
    ) as exc:
        return web.json_response(
            {
                "error": str(exc),
            },
            status=502,
        )
