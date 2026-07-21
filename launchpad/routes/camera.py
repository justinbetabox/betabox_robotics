from __future__ import annotations

import aiohttp_jinja2

from aiohttp import web


async def camera_page(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "camera.html",
        request,
        {
            "page": {
                "title": "Vision",
                "eyebrow": "Betabox Vision",
                "main_class": "camera-main",
            },
        },
    )


def setup_camera_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/camera",
        camera_page,
        name="camera-page",
    )
