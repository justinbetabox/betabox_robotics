from __future__ import annotations

import asyncio
import subprocess

import aiohttp_jinja2
from aiohttp import web

from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
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
            check=False,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return "unknown"

    return result.stdout.strip() or result.stderr.strip() or "unknown"


def jupyter_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.CODE)

    return context


async def jupyter_status(
    request: web.Request,
) -> web.Response:
    context = jupyter_context(request)

    platform = context.platform
    unit = platform.services.jupyterhub.unit

    state = await asyncio.to_thread(
        service_state,
        unit,
    )

    responding = False
    health_message = "Service is not active."

    if state == "active":
        (
            responding,
            health_message,
        ) = await asyncio.to_thread(
            check_http_available,
            platform.network.jupyterhub_health_url,
        )

    return web.json_response(
        {
            "service": "jupyterhub",
            "unit": unit,
            "active": state == "active",
            "responding": responding,
            "state": state,
            "health_message": health_message,
            "port": platform.network.jupyterhub_port,
        }
    )


async def jupyter_page(
    request: web.Request,
) -> web.Response:
    _ = jupyter_context(request)

    return aiohttp_jinja2.render_template(
        "jupyter.html",
        request,
        {
            "page": {
                "title": "JupyterLab",
                "eyebrow": "Betabox Coding",
                "main_class": ("page-layout jupyter-layout"),
            },
        },
    )


def setup_jupyter_routes(
    app: web.Application,
) -> None:
    _ = app.router.add_get(
        "/jupyter",
        jupyter_page,
        name="jupyter-page",
    )

    _ = app.router.add_get(
        "/api/jupyter/status",
        jupyter_status,
        name="jupyter-status-api",
    )
