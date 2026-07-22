from __future__ import annotations

import asyncio

import lgpio

from collections.abc import Callable

from gpiozero.exc import GPIOPinInUse

from time import sleep

import aiohttp_jinja2

from aiohttp import web

from betabox_robotics.services.calibration import (
    CalibrationService,
)

from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
)
from betabox_robotics.sensors import (
    Grayscale,
)
from betabox_robotics.drive import Drive
from betabox_robotics.exceptions import (
    RobotBusyError,
)
from betabox_robotics.camera import (
    CameraMount,
)

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
    *,
    failure_message: str,
    **kwargs: object,
) -> web.Response:
    try:
        await asyncio.to_thread(
            preview,
            **kwargs,
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
                "The robot hardware is currently "
                "being used by another application."
            ),
            detail=str(exc),
            status=409,
        )

    except Exception as exc:
        return error_response(
            error="preview_failed",
            message=failure_message,
            detail=str(exc),
            status=500,
        )

def sample_grayscale(
    *,
    samples: int = 10,
) -> list[int]:
    if samples < 1:
        raise ValueError(
            "samples must be at least 1"
        )

    totals = [
        0.0,
        0.0,
        0.0,
    ]

    with Grayscale.default(
        BETABOX_CAR.sensors.grayscale
    ) as grayscale:
        for _ in range(samples):
            values = grayscale.read()

            totals[0] += values[0]
            totals[1] += values[1]
            totals[2] += values[2]

    return [
        round(total / samples)
        for total in totals
    ]

def preview_steering(
    *,
    offset: float,
) -> None:
    steering_config = (
        BETABOX_CAR.drive.steering
    )

    minimum = steering_config.min_angle
    maximum = steering_config.max_angle

    if not minimum <= offset <= maximum:
        raise ValueError(
            "steering offset must be between "
            f"{minimum} and {maximum}"
        )

    try:
        with Drive.default(
            BETABOX_CAR.drive,
            steering_offset=offset,
        ) as drive:
            drive.center()

    except (
        GPIOPinInUse,
        lgpio.error,
    ) as exc:
        raise RobotBusyError(
            "The steering hardware could not be "
            "acquired. Another process may be "
            "using the robot."
        ) from exc

def preview_camera_mount(
    *,
    pan_offset: float,
    tilt_offset: float,
) -> None:
    config = BETABOX_CAR.camera_mount

    if not (
        config.pan_min_angle
        <= pan_offset
        <= config.pan_max_angle
    ):
        raise ValueError(
            "pan offset is out of range"
        )

    if not (
        config.tilt_min_angle
        <= tilt_offset
        <= config.tilt_max_angle
    ):
        raise ValueError(
            "tilt offset is out of range"
        )

    try:
        with CameraMount.default(
            config,
            pan_offset=pan_offset,
            tilt_offset=tilt_offset,
        ) as camera:
            camera.center()

    except (
        GPIOPinInUse,
        lgpio.error,
    ) as exc:
        raise RobotBusyError(
            "The camera hardware could not be "
            "acquired. Another process may be "
            "using the robot."
        ) from exc

def preview_motor_trim(
    *,
    left_trim: float,
    right_trim: float,
    steering_offset: float,
) -> None:
    if not 0.0 <= left_trim <= 1.0:
        raise ValueError(
            "left trim must be between 0 and 1."
        )

    if not 0.0 <= right_trim <= 1.0:
        raise ValueError(
            "right trim must be between 0 and 1."
        )

    try:
        with Drive.default(
            BETABOX_CAR.drive,
            left_trim=left_trim,
            right_trim=right_trim,
            steering_offset=steering_offset,
        ) as drive:
            drive.center()

            try:
                drive.forward(
                    25
                )

                sleep(
                    1.5
                )
            finally:
                drive.stop()

    except (
        GPIOPinInUse,
        lgpio.error,
    ) as exc:
        raise RobotBusyError(
            "The drive hardware could not be "
            "acquired. Another process may be "
            "using the robot."
        ) from exc

def calibration_response(
    service: CalibrationService,
) -> web.Response:
    return web.json_response(
        service.status().to_dict()
    )

async def calibration_page(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "calibration.html",
        request,
        {
            "page": {
                "title": "Calibration",
                "eyebrow": "Robot Setup",
                "main_class": "page-layout calibration-layout"
            },
        },
    )

async def calibration_api(
    request: web.Request,
) -> web.Response:
    service: CalibrationService = request.app[
        "calibration_service"
    ]

    try:
        return calibration_response(
            service
        )
    except Exception as exc:
        return error_response(
            error="calibration_unavailable",
            message=(
                "Unable to load robot calibration."
            ),
            detail=str(exc),
            status=500,
        )

async def sample_grayscale_api(
    request: web.Request,
) -> web.Response:
    try:
        values = sample_grayscale()

        return web.json_response(
            {
                "values": values,
            }
        )

    except Exception as exc:
        return error_response(
            error="sample_failed",
            message=(
                "Unable to read the line "
                "sensor."
            ),
            detail=str(exc),
            status=500,
        )


async def update_motors_api(
    request: web.Request,
) -> web.Response:
    service: CalibrationService = request.app[
        "calibration_service"
    ]

    try:
        body = await request.json()

        if not isinstance(body, dict):
            raise TypeError

        left_trim = float(
            body["left_trim"]
        )

        right_trim = float(
            body["right_trim"]
        )

        service.update_motors(
            left_trim=left_trim,
            right_trim=right_trim,
        )

        return calibration_response(
            service
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=(
                "Valid left and right motor "
                "trim values are required."
            ),
            status=400,
        )

    except Exception as exc:
        return error_response(
            error="update_failed",
            message=(
                "Unable to save motor trim "
                "calibration."
            ),
            detail=str(exc),
            status=500,
        )

async def update_steering_api(
    request: web.Request,
) -> web.Response:
    service: CalibrationService = request.app[
        "calibration_service"
    ]

    try:
        body = await request.json()

        if not isinstance(body, dict):
            raise TypeError

        offset = float(
            body["offset"]
        )

        service.update_steering(
            offset=offset,
        )

        return calibration_response(
            service
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=(
                "A valid steering offset "
                "is required."
            ),
            status=400,
        )

    except Exception as exc:
        return error_response(
            error="update_failed",
            message=(
                "Unable to save steering "
                "calibration."
            ),
            detail=str(exc),
            status=500,
        )

async def preview_steering_api(
    request: web.Request,
) -> web.Response:
    try:
        body = await request.json()

        if not isinstance(body, dict):
            raise TypeError

        offset = float(
            body["offset"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=(
                "A valid steering offset "
                "is required."
            ),
            status=400,
        )

    return await run_preview(
        preview_steering,
        failure_message=(
            "Unable to move the steering servo."
        ),
        offset=offset,
    )

async def preview_camera_mount_api(
    request: web.Request,
) -> web.Response:
    try:
        body = await request.json()

        if not isinstance(body, dict):
            raise TypeError

        pan_offset = float(
            body["pan_offset"]
        )

        tilt_offset = float(
            body["tilt_offset"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=(
                "Valid camera pan and tilt "
                "offsets are required."
            ),
            status=400,
        )

    return await run_preview(
        preview_camera_mount,
        failure_message=(
            "Unable to move the camera mount."
        ),
        pan_offset=pan_offset,
        tilt_offset=tilt_offset,
    )

async def preview_motor_trim_api(
    request: web.Request,
) -> web.Response:
    service = request.app[
        "calibration_service"
    ]

    try:
        body = await request.json()

        if not isinstance(
            body,
            dict,
        ):
            raise TypeError

        left_trim = float(
            body["left_trim"]
        )

        right_trim = float(
            body["right_trim"]
        )

        calibration = (
            service.load()
        )

    except (
        KeyError,
        TypeError,
    ):
        return error_response(
            error="invalid_request",
            message=(
                "Valid left and right motor "
                "trim values are required."
            ),
            status=400,
        )

    return await run_preview(
        preview_motor_trim,
        failure_message=(
            "Unable to preview motor trim."
        ),
        left_trim=left_trim,
        right_trim=right_trim,
        steering_offset=(
            calibration
            .steering
            .offset
        ),
    )

async def update_camera_mount_api(
    request: web.Request,
) -> web.Response:
    service: CalibrationService = request.app[
        "calibration_service"
    ]

    try:
        body = await request.json()

        if not isinstance(body, dict):
            raise TypeError

        pan_offset = float(
            body["pan_offset"]
        )

        tilt_offset = float(
            body["tilt_offset"]
        )

        service.update_camera_mount(
            pan_offset=pan_offset,
            tilt_offset=tilt_offset,
        )

        return calibration_response(
            service
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=(
                "Valid camera pan and tilt "
                "offsets are required."
            ),
            status=400,
        )

    except Exception as exc:
        return error_response(
            error="update_failed",
            message=(
                "Unable to save camera mount "
                "calibration."
            ),
            detail=str(exc),
            status=500,
        )

async def update_grayscale_api(
    request: web.Request,
) -> web.Response:
    service: CalibrationService = request.app[
        "calibration_service"
    ]

    try:
        body = await request.json()

        if not isinstance(body, dict):
            raise TypeError

        floor = body["floor"]
        line = body["line"]

        if (
            not isinstance(floor, list)
            or not isinstance(line, list)
        ):
            raise TypeError

        service.update_grayscale(
            floor=floor,
            line=line,
        )

        return calibration_response(
            service
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return error_response(
            error="invalid_request",
            message=(
                "Valid floor and line sensor "
                "readings are required."
            ),
            status=400,
        )

    except Exception as exc:
        return error_response(
            error="update_failed",
            message=(
                "Unable to save line sensor "
                "calibration."
            ),
            detail=str(exc),
            status=500,
        )

async def clear_grayscale_api(
    request: web.Request,
) -> web.Response:
    service: CalibrationService = request.app[
        "calibration_service"
    ]

    try:
        service.clear_grayscale()

        return calibration_response(
            service
        )

    except Exception as exc:
        return error_response(
            error="clear_failed",
            message=(
                "Unable to clear line sensor "
                "calibration."
            ),
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
