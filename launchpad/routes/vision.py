from __future__ import annotations

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
)


def vision_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.VISION)

    return context


async def vision_page(
    request: web.Request,
) -> web.Response:
    vision_context(request)

    return aiohttp_jinja2.render_template(
        "vision.html",
        request,
        {
            "page": {
                "title": "Vision",
                "eyebrow": "Betabox Vision",
                "main_class": ("interior-content-full vision-main"),
            },
        },
    )


def setup_vision_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/vision",
        vision_page,
        name="vision-page",
    )
