from __future__ import annotations

import json
from uuid import uuid4

import aiohttp
import aiohttp_jinja2
from aiohttp import WSMsgType, web

from betabox_robotics.exceptions import (
    RobotBusyError,
)
from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
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

    raise DriveControlError(f"{name} must be a boolean")


def drive_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.ROBOT_DRIVE)

    return context


def vision_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.VISION)

    return context


async def drive_page(
    request: web.Request,
) -> web.Response:
    drive_context(request)

    return aiohttp_jinja2.render_template(
        "drive.html",
        request,
        {
            "page": {
                "title": "Manual Drive",
                "eyebrow": "Robot Control",
                "main_class": ("interior-content-wide drive-layout"),
            },
        },
    )


async def drive_websocket(
    request: web.Request,
) -> web.WebSocketResponse:
    context = drive_context(request)

    controller = context.services.require_drive_controller()

    websocket = web.WebSocketResponse(
        heartbeat=10.0,
        receive_timeout=15.0,
    )

    await websocket.prepare(request)

    client_id = uuid4().hex

    try:
        try:
            claimed = await controller.claim(client_id)

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

        except (
            DriveControlError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            await send_json_if_open(
                websocket,
                {
                    "type": "error",
                    "message": (f"Manual Drive could not start: {exc}"),
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
                        "The robot is already being controlled from another browser."
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
                "heartbeat_timeout": (controller.heartbeat_timeout),
            }
        )

        while not websocket.closed:
            try:
                message = await websocket.receive(timeout=0.25)

            except TimeoutError:
                still_owns_robot = await controller.owns(client_id)

                if not still_owns_robot:
                    await websocket.close(
                        code=4003,
                        message=b"manual drive heartbeat timed out",
                    )
                    break

                continue

            if message.type == WSMsgType.TEXT:
                await handle_drive_message(
                    websocket,
                    controller,
                    client_id,
                    message.data,
                )
                continue

            if message.type in (
                WSMsgType.CLOSE,
                WSMsgType.CLOSING,
                WSMsgType.CLOSED,
                WSMsgType.ERROR,
            ):
                break

    finally:
        try:
            await controller.release(client_id)
        except DriveControlError:
            pass

    return websocket


async def send_json_if_open(
    websocket: web.WebSocketResponse,
    data: dict[str, object],
) -> bool:
    if websocket.closed:
        return False

    try:
        await websocket.send_json(data)
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
            raise DriveControlError("message must be a JSON object")

        message_type = data.get("type")

        if not isinstance(
            message_type,
            str,
        ):
            raise DriveControlError("message type must be a string")

        if message_type == "heartbeat":
            await controller.heartbeat(client_id)

            await send_json_if_open(
                websocket,
                {
                    "type": "heartbeat",
                },
            )
            return

        if message_type == "stop":
            await controller.emergency_stop(client_id)

            await send_json_if_open(
                websocket,
                {
                    "type": "stopped",
                },
            )
            return

        if message_type != "control":
            raise DriveControlError("unknown manual-control message type")

        state = ControlState(
            throttle=float(data.get("throttle", 0.0)),
            steering=float(data.get("steering", 0.0)),
            camera_pan=float(data.get("camera_pan", 0.0)),
            camera_tilt=float(data.get("camera_tilt", 0.0)),
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


async def vision_offer_proxy(
    request: web.Request,
) -> web.Response:
    context = vision_context(request)

    platform = context.platform

    try:
        offer = await request.json()

        if not isinstance(
            offer,
            dict,
        ):
            raise TypeError("offer must be a JSON object")

        sdp = offer.get("sdp")
        offer_type = offer.get("type")

        if (
            not isinstance(
                sdp,
                str,
            )
            or not sdp
        ):
            raise ValueError("offer sdp must be a non-empty string")

        if (
            not isinstance(
                offer_type,
                str,
            )
            or not offer_type
        ):
            raise ValueError("offer type must be a non-empty string")

        vision_url = f"{platform.network.vision_url}/offer"

        timeout = aiohttp.ClientTimeout(total=10)

        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(
                vision_url,
                json={
                    "sdp": sdp,
                    "type": offer_type,
                },
            ) as response,
        ):
            try:
                response_data = await response.json()

            except (
                json.JSONDecodeError,
                aiohttp.ContentTypeError,
            ) as exc:
                return web.json_response(
                    {
                        "error": ("Vision signaling returned an invalid response."),
                        "detail": str(exc),
                    },
                    status=502,
                )

            if response.status >= 400:
                return web.json_response(
                    {
                        "error": ("Vision signaling request failed"),
                        "details": response_data,
                    },
                    status=response.status,
                )

        return web.json_response(response_data)

    except (
        TypeError,
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
        TimeoutError,
        aiohttp.ClientError,
    ) as exc:
        return web.json_response(
            {
                "error": str(exc),
            },
            status=502,
        )


def setup_drive_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/drive",
        drive_page,
        name="drive-page",
    )

    app.router.add_get(
        "/ws/drive",
        drive_websocket,
        name="drive-websocket",
    )

    app.router.add_post(
        "/api/vision/offer",
        vision_offer_proxy,
        name="vision-offer-api",
    )
