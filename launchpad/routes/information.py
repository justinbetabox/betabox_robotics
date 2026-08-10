from __future__ import annotations

import asyncio

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
)
from betabox_robotics.services.platform_information import (
    collect_platform_information,
)

_INFORMATION_COLLECTION_ERRORS = (
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def information_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.INFORMATION)

    return context


async def information_page(
    request: web.Request,
) -> web.Response:
    information_context(request)

    return aiohttp_jinja2.render_template(
        "information.html",
        request,
        {
            "page": {
                "title": "Information",
                "eyebrow": "Robot Details",
                "main_class": "page-layout information-layout",
            },
        },
    )


async def information_api(
    request: web.Request,
) -> web.Response:
    """
    Return safe, user-facing platform information.

    The endpoint is read-only and deliberately does not expose the
    complete PlatformConfig or administrative configuration values.
    """

    context = information_context(request)

    try:
        report = await asyncio.to_thread(
            collect_platform_information,
            context.platform,
        )

    except _INFORMATION_COLLECTION_ERRORS as exc:
        return web.json_response(
            {
                "error": "information_unavailable",
                "message": "Unable to collect platform information.",
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(report.to_dict())


def setup_information_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/information",
        information_page,
        name="information-page",
    )

    app.router.add_get(
        "/api/information",
        information_api,
        name="information-api",
    )
