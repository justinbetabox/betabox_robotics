from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from typing import cast

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.calibration.hardware import (
    CalibrationHardware,
)
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


def _validate_float(
    value: object,
    *,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError(f"{name} must be a number")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")

    return result


def _validate_float_list(
    value: object,
    *,
    name: str,
) -> list[float]:
    if not isinstance(
        value,
        list,
    ):
        raise TypeError(f"{name} must be a list")

    values = cast(
        list[object],
        value,
    )

    return [
        _validate_float(
            item,
            name=f"{name} item",
        )
        for item in values
    ]


async def json_object(
    request: web.Request,
) -> dict[str, object]:
    try:
        body = cast(
            object,
            await request.json(),
        )

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

    raw_body = cast(
        dict[object, object],
        body,
    )

    result: dict[str, object] = {}

    for key, value in raw_body.items():
        if not isinstance(
            key,
            str,
        ):
            raise TypeError("request body keys must be strings")

        result[key] = value

    return result


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
    _ = calibration_context(request)

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

        left_trim = _validate_float(
            body["left_trim"],
            name="left_trim",
        )

        right_trim = _validate_float(
            body["right_trim"],
            name="right_trim",
        )

        _ = service.update_motors(
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

        offset = _validate_float(
            body["offset"],
            name="offset",
        )

        _ = service.update_steering(
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

        offset = _validate_float(
            body["offset"],
            name="offset",
        )

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

        pan_offset = _validate_float(
            body["pan_offset"],
            name="pan_offset",
        )

        tilt_offset = _validate_float(
            body["tilt_offset"],
            name="tilt_offset",
        )

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

        left_trim = _validate_float(
            body["left_trim"],
            name="left_trim",
        )

        right_trim = _validate_float(
            body["right_trim"],
            name="right_trim",
        )

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

        pan_offset = _validate_float(
            body["pan_offset"],
            name="pan_offset",
        )

        tilt_offset = _validate_float(
            body["tilt_offset"],
            name="tilt_offset",
        )

        _ = service.update_camera_mount(
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

        floor = _validate_float_list(
            body["floor"],
            name="floor",
        )

        line = _validate_float_list(
            body["line"],
            name="line",
        )

        _ = service.update_grayscale(
            floor=floor,
            line=line,
        )

        return calibration_response(service)

    except KeyError:
        return error_response(
            error="invalid_request",
            message="Floor and line sensor readings are required.",
            status=400,
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        return error_response(
            error="invalid_request",
            message=str(exc),
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
        _ = service.clear_grayscale()

        return calibration_response(service)

    except CalibrationStorageError as exc:
        return error_response(
            error="clear_failed",
            message=("Unable to clear line sensor calibration."),
            detail=str(exc),
            status=500,
        )


async def reset_calibration_api(
    request: web.Request,
) -> web.Response:
    service = calibration_service(request)
    hardware = calibration_hardware(request)

    try:
        await asyncio.to_thread(
            hardware.reset_to_defaults,
        )

        _ = service.reset()

        return calibration_response(service)

    except RobotBusyError as exc:
        return error_response(
            error="robot_busy",
            message=("The robot is currently being used by another application."),
            detail=str(exc),
            status=409,
        )

    except CalibrationStorageError as exc:
        return error_response(
            error="reset_failed",
            message=("Unable to reset robot calibration."),
            detail=str(exc),
            status=500,
        )

    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        return error_response(
            error="reset_failed",
            message=(
                "Unable to return the robot to its default calibration positions."
            ),
            detail=str(exc),
            status=500,
        )


def setup_calibration_routes(
    app: web.Application,
) -> None:
    _ = app.router.add_get(
        "/calibration",
        calibration_page,
        name="calibration-page",
    )

    _ = app.router.add_get(
        "/api/calibration",
        calibration_api,
        name="calibration-api",
    )

    _ = app.router.add_put(
        "/api/calibration/steering",
        update_steering_api,
        name="calibration-steering-api",
    )

    _ = app.router.add_post(
        "/api/calibration/steering/preview",
        preview_steering_api,
        name="calibration-steering-preview-api",
    )

    _ = app.router.add_put(
        "/api/calibration/camera-mount",
        update_camera_mount_api,
        name="calibration-camera-mount-api",
    )

    _ = app.router.add_post(
        "/api/calibration/camera-mount/preview",
        preview_camera_mount_api,
        name="calibration-camera-mount-preview-api",
    )

    _ = app.router.add_put(
        "/api/calibration/motors",
        update_motors_api,
        name="calibration-motors-api",
    )

    _ = app.router.add_post(
        "/api/calibration/motors/preview",
        preview_motor_trim_api,
        name="calibration-motors-preview-api",
    )

    _ = app.router.add_get(
        "/api/calibration/grayscale/sample",
        sample_grayscale_api,
        name="calibration-grayscale-sample-api",
    )

    _ = app.router.add_put(
        "/api/calibration/grayscale",
        update_grayscale_api,
        name="calibration-grayscale-api",
    )

    _ = app.router.add_post(
        "/api/calibration/grayscale/clear",
        clear_grayscale_api,
        name="calibration-grayscale-clear-api",
    )

    _ = app.router.add_post(
        "/api/calibration/reset",
        reset_calibration_api,
        name="calibration-reset-api",
    )
