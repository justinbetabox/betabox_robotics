from __future__ import annotations

import asyncio

from aiohttp import web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.launchpad.routes.services_page import (
    services_page,
)
from betabox_robotics.services.services import (
    collect_services,
    service_summary,
)


async def services_api(
    request: web.Request,
) -> web.Response:
    """
    Return read-only status information for managed platform services.
    """

    config: PlatformConfig = request.app[
        "platform_config"
    ]

    statuses = await asyncio.to_thread(
        collect_services,
        config,
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

    return web.json_response(
        payload
    )


def setup_services_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/services",
        services_page,
    )

    app.router.add_get(
        "/api/services",
        services_api,
    )
