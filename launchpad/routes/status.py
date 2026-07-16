from __future__ import annotations

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.services.http_health import (
    check_http_available,
)
from betabox_robotics.services.platform_summary import (
    collect_platform_summary,
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
                config.services.jupyterhub,
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


def setup_status_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/api/status",
        status_api,
    )
