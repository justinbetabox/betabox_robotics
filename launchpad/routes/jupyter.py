from __future__ import annotations

import asyncio
import subprocess

from aiohttp import web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.launchpad.components import (
    back_link,
    page_heading,
    status_pill,
)
from betabox_robotics.launchpad.layout import (
    render_page,
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
        "service is not active"
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
    body = f"""
<header class="jupyter-header">
    {back_link()}

    {page_heading(
        eyebrow="Betabox Coding",
        title="JupyterLab",
    )}

    {status_pill(
        element_id="jupyter-status",
        text="Checking…",
        css_class=(
            "jupyter-status "
            "status-connecting"
        ),
    )}
</header>

<main class="jupyter-main">
    <section class="jupyter-card">
        <div class="jupyter-card-heading">
            <div>
                <p class="eyebrow">
                    Coding Environment
                </p>

                <h2>
                    Program Your Robot
                </h2>
            </div>

            <span
                id="jupyter-health-dot"
                class="
                    jupyter-health-dot
                    status-unknown
                "
                aria-hidden="true"
            ></span>
        </div>

        <p class="jupyter-description">
            Open JupyterLab to write and run Python code
            using the Betabox Robotics API.
        </p>

        <dl class="jupyter-details">
            <div>
                <dt>Service</dt>
                <dd id="jupyter-service-state">
                    Checking…
                </dd>
            </div>

            <div>
                <dt>HTTP</dt>
                <dd id="jupyter-http-state">
                    Checking…
                </dd>
            </div>

            <div>
                <dt>Port</dt>
                <dd id="jupyter-port">
                    --
                </dd>
            </div>
        </dl>

        <a
            id="open-jupyter"
            class="jupyter-button is-disabled"
            href="#"
            aria-disabled="true"
        >
            Open JupyterLab
        </a>

        <p
            id="jupyter-message"
            class="jupyter-message"
        >
            Checking JupyterHub…
        </p>
    </section>

    <section class="ownership-card">
        <p class="eyebrow">
            Robot Ownership
        </p>

        <h2>
            Close Manual Drive Before Coding
        </h2>

        <p>
            Manual Drive and notebook code cannot control
            the robot at the same time.
        </p>

        <p>
            Close the Manual Drive page before creating a
            <code>BetaboxCar</code> in JupyterLab. When your
            notebook finishes, use a context manager or call
            <code>car.close()</code> so Launchpad can use the
            robot again.
        </p>

        <pre><code>from betabox_robotics import BetaboxCar

with BetaboxCar() as car:
    print(car.distance())</code></pre>
    </section>
</main>
"""

    html = render_page(
        title=(
            "Coding · "
            "Betabox Launchpad"
        ),
        body=body,
        body_class="jupyter-page",
        stylesheets=(
            "/static/jupyter.css",
        ),
        module_scripts=(
            "/static/jupyter.js",
        ),
    )

    return web.Response(
        text=html,
        content_type="text/html",
    )


def setup_jupyter_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/jupyter",
        jupyter_page,
    )

    app.router.add_get(
        "/api/jupyter/status",
        jupyter_status,
    )
