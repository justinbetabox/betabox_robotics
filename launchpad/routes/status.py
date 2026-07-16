from __future__ import annotations

import asyncio

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.services.http_health import (
    check_http_available,
)
from betabox_robotics.services.platform_summary import (
    collect_platform_summary,
)

from betabox_robotics.services.status import (
    collect_status,
)

from betabox_robotics.launchpad.routes.detailed_status import (
    detailed_status_page,
)


async def status_api(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    cache = request.app[
        "status_cache"
    ]

    def collect_payload() -> dict[str, object]:
        summary = collect_platform_summary(
            config
        )

        payload = summary.to_dict()

        jupyter_state = (
            summary.services.get(
                config.services.jupyterhub.unit,
                "unknown",
            )
        )

        jupyter_responding = False
        jupyter_message = (
            "service is not active"
        )

        if jupyter_state == "active":
            (
                jupyter_responding,
                jupyter_message,
            ) = check_http_available(
                config.network.jupyterhub_health_url,
            )

        payload["jupyterhub"] = {
            "state": jupyter_state,
            "active": (
                jupyter_state == "active"
            ),
            "responding": (
                jupyter_responding
            ),
            "message": jupyter_message,
        }

        return payload

    payload = await cache.get(
        collect_payload
    )

    return web.json_response(
        payload
    )


async def detailed_status_api(
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
        report.to_dict()
    )


def setup_status_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/status",
        detailed_status_page,
    )

    app.router.add_get(
        "/api/status",
        status_api,
    )

    app.router.add_get(
        "/api/status/detailed",
        detailed_status_api,
    )
