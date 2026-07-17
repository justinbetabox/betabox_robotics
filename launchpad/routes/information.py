from __future__ import annotations

import asyncio

from aiohttp import web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.launchpad.routes.information_page import (
    information_page,
)
from betabox_robotics.services.platform_information import (
    collect_platform_information,
)


async def information_api(
    request: web.Request,
) -> web.Response:
    """
    Return safe, student-facing platform information.

    The endpoint is read-only and deliberately does not expose the
    complete PlatformConfig or administrative configuration values.
    """

    config: PlatformConfig = request.app[
        "platform_config"
    ]

    try:
        report = await asyncio.to_thread(
            collect_platform_information,
            config,
        )
    except Exception as exc:
        return web.json_response(
            {
                "error": (
                    "information_unavailable"
                ),
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
    )

    app.router.add_get(
        "/api/information",
        information_api,
    )
