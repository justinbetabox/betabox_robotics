from __future__ import annotations

from aiohttp import web

from betabox_robotics.launchpad.components import (
    back_link,
    page_heading,
    status_pill,
)
from betabox_robotics.launchpad.layout import (
    render_page,
)


async def camera_page(
    request: web.Request,
) -> web.Response:
    body = f"""
<header class="camera-header">
    {back_link()}

    {page_heading(
        eyebrow="Betabox Vision",
        title="Live Camera",
    )}

    {status_pill(
        element_id="camera-status",
        text="Connecting…",
        css_class=(
            "camera-status "
            "status-connecting"
        ),
    )}
</header>

<main class="camera-main">
    <section
        class="camera-view"
        data-video-state="connecting"
    >
        <video
            id="live-camera"
            class="camera-video"
            autoplay
            playsinline
            muted
        ></video>

        <div class="camera-message">
            Connecting camera…
        </div>
    </section>
</main>
"""

    html = render_page(
        title=(
            "Live Camera · "
            "Betabox Launchpad"
        ),
        body=body,
        body_class="camera-page",
        stylesheets=(
            "/static/camera.css",
        ),
        module_scripts=(
            "/static/camera.js",
        ),
    )

    return web.Response(
        text=html,
        content_type="text/html",
    )


def setup_camera_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/camera",
        camera_page,
    )
