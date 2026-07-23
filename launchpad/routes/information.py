from __future__ import annotations

import asyncio

import aiohttp_jinja2

from aiohttp import web

from betabox_robotics.services.platform_information import (
    collect_platform_information,
)
from betabox_robotics.launchpad.auth import (
    LaunchpadContext,
)

async def information_page(
    request: web.Request,
) -> web.Response:
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

    context: LaunchpadContext = request[
        "launchpad_context"
    ]

    try:
        report = await asyncio.to_thread(
            collect_platform_information,
            context.platform,
        )
    except Exception as exc:
        return web.json_response(
            {
                "error": "information_unavailable",
                "message": (
                    "Unable to collect platform "
                    "information."
                ),
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(
        report.to_dict()
    )


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
