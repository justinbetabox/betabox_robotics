from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.calibration.storage import (
    CalibrationStorageError,
)
from betabox_robotics.exceptions import (
    RobotBusyError,
)
from betabox_robotics.hardware import (
    HardwareError,
)
from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
)
from betabox_robotics.services.calibration import (
    CalibrationService,
)


async def json_object(
    request: web.Request,
) -> dict[str, Any]:
    try:
        body = await request.json()

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError("request body must be valid JSON") from exc

    if not isinstance(
        body,
        dict,
    ):
        raise TypeError("request body must be a JSON object")

    return body


def calibration_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.CALIBRATION)

    return context


def calibration_service(
    request: web.Request,
) -> CalibrationService:
    context = calibration_context(request)

    return context.services.calibration_service


def calibration_hardware(
    request: web.Request,
) -> CalibrationHardware:
    context = calibration_context(request)

    return context.services.calibration_hardware


def error_response(
    *,
    error: str,
    message: str,
    status: int,
    detail: str | None = None,
) -> web.Response:
    payload: dict[str, object] = {
        "error": error,
        "message": message,
    }

    if detail is not None:
        payload["detail"] = detail

    return web.json_response(
        payload,
        status=status,
    )


async def run_preview(
    preview: Callable[..., None],
    **kwargs: object,
) -> None:
    await asyncio.to_thread(
        preview,
        **kwargs,
    )


def calibration_response(
    service: CalibrationService,
) -> web.Response:
    return web.json_response(service.status().to_dict())


async def calibration_page(
    request: web.Request,
) -> web.Response:
    calibration_context(request)

    return aiohttp_jinja2.render_template(
        "calibration.html",
        request,
        {
            "page": {
                "title": "Calibration",
                "eyebrow": "Robot Setup",
                "main_class": ("page-layout calibration-layout"),
            },
        },
    )


async def calibration_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)

    try:
        return calibration_response(service)

    except CalibrationStorageError as exc:
        return error_response(
            error="calibration_unavailable",
            message=("Unable to load robot calibration."),
            detail=str(exc),
            status=500,
        )


async def sample_grayscale_api(
    request: web.Request,
) -> web.Response:
    hardware = calibration_hardware(request)

    try:
        values = await asyncio.to_thread(
            hardware.sample_grayscale,
        )

        return web.json_response(
            {
                "values": values,
            }
        )

    except RobotBusyError as exc:
        return error_response(
            error="robot_busy",
            message=(
                "The robot hardware is currently being used by another application."
            ),
            detail=str(exc),
            status=409,
        )

    except (
        HardwareError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        return error_response(
            error="sample_failed",
            message="Unable to read the line sensor.",
            detail=str(exc),
            status=500,
        )


async def update_motors_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)

    try:
        body = await json_object(request)

        left_trim = float(body["left_trim"])

        right_trim = float(body["right_trim"])

        service.update_motors(
            left_trim=left_trim,
            right_trim=right_trim,
        )

        return calibration_response(service)

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=("Valid left and right motor trim values are required."),
            status=400,
        )

    except CalibrationStorageError as exc:
        return error_response(
            error="update_failed",
            message=("Unable to save motor trim calibration."),
            detail=str(exc),
            status=500,
        )


async def update_steering_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)

    try:
        body = await json_object(request)

        offset = float(body["offset"])

        service.update_steering(
            offset=offset,
        )

        return calibration_response(service)

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=("A valid steering offset is required."),
            status=400,
        )

    except CalibrationStorageError as exc:
        return error_response(
            error="update_failed",
            message=("Unable to save steering calibration."),
            detail=str(exc),
            status=500,
        )


async def preview_steering_api(
    request: web.Request,
) -> web.Response:
    hardware = calibration_hardware(request)

    try:
        body = await json_object(request)

        offset = float(body["offset"])

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=("A valid steering offset is required."),
            status=400,
        )

    try:
        await run_preview(
            hardware.preview_steering,
            offset=offset,
        )

        return web.json_response(
            {
                "status": "ok",
            }
        )

    except ValueError as exc:
        return error_response(
            error="invalid_request",
            message=str(exc),
            status=400,
        )

    except RobotBusyError as exc:
        return error_response(
            error="robot_busy",
            message=(
                "The robot hardware is currently being used by another application."
            ),
            detail=str(exc),
            status=409,
        )

    except (
        OSError,
        RuntimeError,
    ) as exc:
        return error_response(
            error="preview_failed",
            message=("Unable to move the steering servo."),
            detail=str(exc),
            status=500,
        )


async def preview_camera_mount_api(
    request: web.Request,
) -> web.Response:
    hardware = calibration_hardware(request)

    try:
        body = await json_object(request)

        pan_offset = float(body["pan_offset"])

        tilt_offset = float(body["tilt_offset"])

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=("Valid camera pan and tilt offsets are required."),
            status=400,
        )

    try:
        await run_preview(
            hardware.preview_camera_mount,
            pan_offset=pan_offset,
            tilt_offset=tilt_offset,
        )

        return web.json_response(
            {
                "status": "ok",
            }
        )

    except ValueError as exc:
        return error_response(
            error="invalid_request",
            message=str(exc),
            status=400,
        )

    except RobotBusyError as exc:
        return error_response(
            error="robot_busy",
            message=(
                "The robot hardware is currently being used by another application."
            ),
            detail=str(exc),
            status=409,
        )

    except (
        OSError,
        RuntimeError,
    ) as exc:
        return error_response(
            error="preview_failed",
            message=("Unable to move the camera mount."),
            detail=str(exc),
            status=500,
        )


async def preview_motor_trim_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)
    hardware = calibration_hardware(request)

    try:
        body = await json_object(request)

        left_trim = float(body["left_trim"])

        right_trim = float(body["right_trim"])

        calibration = service.load()

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=("Valid left and right motor trim values are required."),
            status=400,
        )

    except CalibrationStorageError as exc:
        return error_response(
            error="calibration_unavailable",
            message=("Unable to load robot calibration."),
            detail=str(exc),
            status=500,
        )

    try:
        await run_preview(
            hardware.preview_motor_trim,
            left_trim=left_trim,
            right_trim=right_trim,
            steering_offset=calibration.steering.offset,
        )

        return web.json_response(
            {
                "status": "ok",
            }
        )

    except ValueError as exc:
        return error_response(
            error="invalid_request",
            message=str(exc),
            status=400,
        )

    except RobotBusyError as exc:
        return error_response(
            error="robot_busy",
            message=(
                "The robot hardware is currently being used by another application."
            ),
            detail=str(exc),
            status=409,
        )

    except (
        OSError,
        RuntimeError,
    ) as exc:
        return error_response(
            error="preview_failed",
            message=("Unable to preview motor trim."),
            detail=str(exc),
            status=500,
        )


async def update_camera_mount_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)

    try:
        body = await json_object(request)

        pan_offset = float(body["pan_offset"])

        tilt_offset = float(body["tilt_offset"])

        service.update_camera_mount(
            pan_offset=pan_offset,
            tilt_offset=tilt_offset,
        )

        return calibration_response(service)

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=("Valid camera pan and tilt offsets are required."),
            status=400,
        )

    except CalibrationStorageError as exc:
        return error_response(
            error="update_failed",
            message=("Unable to save camera mount calibration."),
            detail=str(exc),
            status=500,
        )


async def update_grayscale_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)

    try:
        body = await json_object(request)

        floor = body["floor"]
        line = body["line"]

        if not isinstance(
            floor,
            list,
        ) or not isinstance(
            line,
            list,
        ):
            raise TypeError("floor and line must be lists")

        service.update_grayscale(
            floor=floor,
            line=line,
        )

        return calibration_response(service)

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=("Valid floor and line sensor readings are required."),
            status=400,
        )

    except CalibrationStorageError as exc:
        return error_response(
            error="update_failed",
            message=("Unable to save line sensor calibration."),
            detail=str(exc),
            status=500,
        )


async def clear_grayscale_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)

    try:
        service.clear_grayscale()

        return calibration_response(service)

    except CalibrationStorageError as exc:
        return error_response(
            error="clear_failed",
            message=("Unable to clear line sensor calibration."),
            detail=str(exc),
            status=500,
        )


def setup_calibration_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/calibration",
        calibration_page,
        name="calibration-page",
    )

    app.router.add_get(
        "/api/calibration",
        calibration_api,
        name="calibration-api",
    )

    app.router.add_put(
        "/api/calibration/steering",
        update_steering_api,
        name="calibration-steering-api",
    )

    app.router.add_post(
        "/api/calibration/steering/preview",
        preview_steering_api,
        name="calibration-steering-preview-api",
    )

    app.router.add_put(
        "/api/calibration/camera-mount",
        update_camera_mount_api,
        name="calibration-camera-mount-api",
    )

    app.router.add_post(
        "/api/calibration/camera-mount/preview",
        preview_camera_mount_api,
        name="calibration-camera-mount-preview-api",
    )

    app.router.add_put(
        "/api/calibration/motors",
        update_motors_api,
        name="calibration-motors-api",
    )

    app.router.add_post(
        "/api/calibration/motors/preview",
        preview_motor_trim_api,
        name="calibration-motors-preview-api",
    )

    app.router.add_get(
        "/api/calibration/grayscale/sample",
        sample_grayscale_api,
        name="calibration-grayscale-sample-api",
    )

    app.router.add_put(
        "/api/calibration/grayscale",
        update_grayscale_api,
        name="calibration-grayscale-api",
    )

    app.router.add_post(
        "/api/calibration/grayscale/clear",
        clear_grayscale_api,
        name="calibration-grayscale-clear-api",
    )
