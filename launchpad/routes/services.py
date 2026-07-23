from __future__ import annotations

import asyncio

import aiohttp_jinja2

from aiohttp import web

from betabox_robotics.services.services import (
    collect_services,
    service_summary,
)
from betabox_robotics.launchpad.auth import (
    LaunchpadContext,
)


async def services_page(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "services.html",
        request,
        {
            "page": {
                "title": "Services",
                "eyebrow": "Platform Services",
                "main_class": "page-layout",
            },
        },
    )


async def services_api(
    request: web.Request,
) -> web.Response:
    """
    Return read-only status information for managed platform services.
    """

    context: LaunchpadContext = request[
        "launchpad_context"
    ]

    try:
        statuses = await asyncio.to_thread(
            collect_services,
            context.platform,
        )
    except Exception as exc:
        return web.json_response(
            {
                "error": "services_unavailable",
                "message": (
                    "Unable to collect platform "
                    "service information."
                ),
                "detail": str(exc),
            },
            status=500,
        )

    payload = {
        "summary": service_summary(
            statuses
        ),
        "services": [
            status.to_dict()
            for status in statuses
        ],
    }

    return web.json_response(payload)


def setup_services_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/services",
        services_page,
        name="services-page",
    )

    app.router.add_get(
        "/api/services",
        services_api,
        name="services-api",
    )
