from __future__ import annotations

import aiohttp_jinja2
import asyncio

from aiohttp import web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.services.http_health import (
    check_http_available,
)
from betabox_robotics.services.platform_summary import (
    collect_platform_summary,
)
from betabox_robotics.services.status import (
    collect_status,
)


async def status_page(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "status.html",
        request,
        {
            "page": {
                "title": "Robot Status",
                "eyebrow": "Platform Diagnostics",
                "main_class": "status-layout",
            },
        },
    )


async def status_api(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    cache = request.app[
        "status_cache"
    ]

    def collect_payload() -> dict[str, object]:
        summary = collect_platform_summary(
            config
        )

        payload = summary.to_dict()

        jupyter_state = summary.services.get(
            config.services.jupyterhub.unit,
            "unknown",
        )

        jupyter_responding = False
        jupyter_message = (
            "Service is not active."
        )

        if jupyter_state == "active":
            (
                jupyter_responding,
                jupyter_message,
            ) = check_http_available(
                config.network.jupyterhub_health_url,
            )

        payload["jupyterhub"] = {
            "state": jupyter_state,
            "active": (
                jupyter_state == "active"
            ),
            "responding": jupyter_responding,
            "message": jupyter_message,
        }

        return payload

    try:
        payload = await cache.get(
            collect_payload
        )
    except Exception as exc:
        return web.json_response(
            {
                "error": "status_unavailable",
                "message": (
                    "Unable to collect platform status."
                ),
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(payload)


async def status_report_api(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    try:
        report = await asyncio.to_thread(
            collect_status,
            config,
        )
    except Exception as exc:
        return web.json_response(
            {
                "error": (
                    "status_report_unavailable"
                ),
                "message": (
                    "Unable to collect the full "
                    "platform status report."
                ),
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(
        report.to_dict()
    )


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
        name="detailed-status-api",
    )
