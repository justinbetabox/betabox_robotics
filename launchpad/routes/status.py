from __future__ import annotations

import asyncio

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
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


def status_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.STATUS)

    return context


async def status_page(
    request: web.Request,
) -> web.Response:
    status_context(request)

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

        payload = report.to_dict()

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
            "active": (jupyter_state == "active"),
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

    return web.json_response(report.to_dict())


def setup_status_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/status",
        status_page,
        name="status-page",
    )

    app.router.add_get(
        "/api/status",
        status_api,
        name="status-api",
    )

    app.router.add_get(
        "/api/status/report",
        status_report_api,
        name="status-report-api",
    )
