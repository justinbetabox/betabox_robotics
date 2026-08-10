from __future__ import annotations

import asyncio

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
)
from betabox_robotics.services.services import (
    collect_services,
    service_summary,
)

_SERVICE_COLLECTION_ERRORS = (
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def services_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.SERVICES)

    return context


async def services_page(
    request: web.Request,
) -> web.Response:
    services_context(request)

    return aiohttp_jinja2.render_template(
        "services.html",
        request,
        {
            "page": {
                "title": "Services",
                "eyebrow": "Platform Services",
                "main_class": "page-layout services-layout",
            },
        },
    )


async def services_api(
    request: web.Request,
) -> web.Response:
    """
    Return read-only status information for managed platform services.
    """

    context = services_context(request)

    try:
        statuses = await asyncio.to_thread(
            collect_services,
            context.platform,
        )
    except _SERVICE_COLLECTION_ERRORS as exc:
        return web.json_response(
            {
                "error": "services_unavailable",
                "message": "Unable to collect platform service information.",
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(
        {
            "summary": service_summary(
                statuses,
            ),
            "services": [status.to_dict() for status in statuses],
        }
    )


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
