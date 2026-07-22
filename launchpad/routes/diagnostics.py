from __future__ import annotations

import asyncio

import aiohttp_jinja2

from aiohttp import web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.services.doctor import (
    collect_doctor_report,
)


async def diagnostics_page(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "diagnostics.html",
        request,
        {
            "page": {
                "title": "Diagnostics",
                "eyebrow": "Platform Health",
                "main_class": "page-layout diagnostics-layout",
            },
        },
    )


async def diagnostics_api(
    request: web.Request,
) -> web.Response:
    """
    Run the safe Betabox diagnostic checks and return the report.

    Diagnostics may perform filesystem, hardware, HTTP, and systemd
    checks, so collection runs in a worker thread rather than blocking
    the aiohttp event loop.
    """

    config: PlatformConfig = request.app[
        "platform_config"
    ]

    try:
        report = await asyncio.to_thread(
            collect_doctor_report,
            config,
        )
    except Exception:
        return web.json_response(
            {
                "error": "diagnostics_unavailable",
                "message": (
                    "Unable to run platform diagnostics."
                ),
            },
            status=500,
        )

    return web.json_response(
        report.to_dict()
    )


def setup_diagnostics_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/diagnostics",
        diagnostics_page,
        name="diagnostics-page",
    )

    app.router.add_get(
        "/api/diagnostics",
        diagnostics_api,
        name="diagnostics-api",
    )
