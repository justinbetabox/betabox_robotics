from __future__ import annotations

from dataclasses import asdict

from aiohttp import web
import asyncio

from betabox_robotics.config import PlatformConfig
from betabox_robotics.services.status import collect_status


async def status_api(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    report = await asyncio.to_thread(
        collect_status,
        config,
    )

    return web.json_response(
        asdict(report)
    )


def setup_status_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/api/status",
        status_api,
    )
