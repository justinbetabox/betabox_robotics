from __future__ import annotations

import asyncio
from typing import cast

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.launchpad.auth.context import (
    LaunchpadContext,
)
from betabox_robotics.launchpad.auth.permissions import (
    Permission,
)
from betabox_robotics.launchpad.auth.provider import (
    LAUNCHPAD_CONTEXT_KEY,
)
from betabox_robotics.services.http_health import (
    check_http_available,
)
from betabox_robotics.services.status import (
    collect_status,
)

_STATUS_COLLECTION_ERRORS = (
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def _validate_context(
    value: object,
) -> LaunchpadContext:
    if not isinstance(
        value,
        LaunchpadContext,
    ):
        raise TypeError("request context must be a LaunchpadContext")

    return value


def status_context(
    request: web.Request,
) -> LaunchpadContext:
    raw_context = cast(
        object,
        request[LAUNCHPAD_CONTEXT_KEY],
    )

    context = _validate_context(raw_context)

    context.require(Permission.STATUS)

    return context


async def status_page(
    request: web.Request,
) -> web.Response:
    _ = status_context(request)

    return aiohttp_jinja2.render_template(
        "status.html",
        request,
        {
            "page": {
                "title": "Robot Status",
                "eyebrow": "Platform Diagnostics",
                "main_class": ("page-layout status-layout"),
            },
        },
    )


async def status_api(
    request: web.Request,
) -> web.Response:
    context = status_context(request)

    platform = context.platform
    services = context.services

    def collect_payload() -> dict[str, object]:
        report = collect_status(platform)

        payload: dict[str, object] = {}

        for key, value in report.to_dict(platform).items():
            payload[key] = value

        jupyter_state = report.services.get(
            platform.services.jupyterhub.unit,
            "unknown",
        )

        jupyter_responding = False
        jupyter_message = "Service is not active."

        if jupyter_state == "active":
            (
                jupyter_responding,
                jupyter_message,
            ) = check_http_available(
                platform.network.jupyterhub_health_url,
            )

        payload["jupyterhub"] = {
            "state": jupyter_state,
            "active": jupyter_state == "active",
            "responding": jupyter_responding,
            "message": jupyter_message,
        }

        return payload

    try:
        payload = await services.status_cache.get(collect_payload)

    except _STATUS_COLLECTION_ERRORS as exc:
        return web.json_response(
            {
                "error": "status_unavailable",
                "message": ("Unable to collect platform status."),
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(payload)


async def status_report_api(
    request: web.Request,
) -> web.Response:
    context = status_context(request)

    platform = context.platform

    try:
        report = await asyncio.to_thread(
            collect_status,
            platform,
        )

    except _STATUS_COLLECTION_ERRORS as exc:
        return web.json_response(
            {
                "error": ("status_report_unavailable"),
                "message": ("Unable to collect the full platform status report."),
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(report.to_dict(platform))


def setup_status_routes(
    app: web.Application,
) -> None:
    _ = app.router.add_get(
        "/status",
        status_page,
        name="status-page",
    )

    _ = app.router.add_get(
        "/api/status",
        status_api,
        name="status-api",
    )

    _ = app.router.add_get(
        "/api/status/report",
        status_report_api,
        name="status-report-api",
    )
