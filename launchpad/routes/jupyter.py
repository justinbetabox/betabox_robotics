from __future__ import annotations

import subprocess

import aiohttp_jinja2
import asyncio

from aiohttp import web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.services.http_health import (
    check_http_available,
)


def service_state(
    unit: str,
) -> str:
    try:
        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                unit,
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return "unknown"

    return (
        result.stdout.strip()
        or "unknown"
    )


async def jupyter_status(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    unit = config.services.jupyterhub.unit

    state = await asyncio.to_thread(
        service_state,
        unit,
    )

    responding = False
    health_message = (
        "Service is not active."
    )

    if state == "active":
        responding, health_message = (
            await asyncio.to_thread(
                check_http_available,
                config.network.jupyterhub_health_url,
            )
        )

    return web.json_response(
        {
            "service": "jupyterhub",
            "unit": unit,
            "active": state == "active",
            "responding": responding,
            "state": state,
            "health_message": health_message,
            "port": (
                config.network.jupyterhub_port
            ),
        }
    )


async def jupyter_page(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "jupyter.html",
        request,
        {
            "page": {
                "title": "JupyterLab",
                "eyebrow": "Betabox Coding",
                "main_class": "jupyter-main",
            },
        },
    )


def setup_jupyter_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/jupyter",
        jupyter_page,
        name="jupyter-page",
    )

    app.router.add_get(
        "/api/jupyter/status",
        jupyter_status,
        name="jupyter-status-api",
    )
