from __future__ import annotations

from aiohttp import web


async def camera_page(
    request: web.Request,
) -> web.Response:
    html = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>Live Camera · Betabox Launchpad</title>

    <link
        rel="stylesheet"
        href="/static/launchpad.css"
    >
    <link
        rel="stylesheet"
        href="/static/camera.css"
    >
</head>

<body class="camera-page">
    <header class="camera-header">
        <a class="back-link" href="/">
            ← Launchpad
        </a>

        <div>
            <p class="eyebrow">Betabox Vision</p>
            <h1>Live Camera</h1>
        </div>

        <div
            id="camera-status"
            class="camera-status status-connecting"
        >
            Connecting…
        </div>
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

    <script
        type="module"
        src="/static/camera.js"
    ></script>
</body>
</html>
"""

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
