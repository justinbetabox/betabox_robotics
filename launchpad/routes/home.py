from __future__ import annotations

from html import escape

from aiohttp import web

from betabox_robotics.config import PlatformConfig


def tool_card(
    *,
    title: str,
    description: str,
    href: str,
    css_class: str = "",
) -> str:
    return f"""
    <a class="tool-card {escape(css_class)}"
       href="{escape(href)}">
        <h2>{escape(title)}</h2>
        <p>{escape(description)}</p>
    </a>
    """


async def home(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    student_tools = "".join(
        [
            tool_card(
                title="Manual Drive",
                description=(
                    "Control the robot from your browser."
                ),
                href="/drive",
            ),
            tool_card(
                title="Coding",
                description=(
                    "Open the JupyterLab coding environment."
                ),
                href="/jupyter",
            ),
            tool_card(
                title="Live Camera",
                description=(
                    "View the robot's live camera feed."
                ),
                href="/camera",
            ),
            tool_card(
                title="Media",
                description=(
                    "Browse pictures, videos, and sounds."
                ),
                href="/media",
            ),
            tool_card(
                title="Calibration",
                description=(
                    "Run guided robot calibration tools."
                ),
                href="/calibration",
            ),
        ]
    )

    teacher_tools = "".join(
        [
            tool_card(
                title="Diagnostics",
                description=(
                    "Run status, Verify, and Doctor."
                ),
                href="/teacher/diagnostics",
                css_class="teacher-card",
            ),
            tool_card(
                title="Services",
                description=(
                    "Inspect and manage platform services."
                ),
                href="/teacher/services",
                css_class="teacher-card",
            ),
            tool_card(
                title="Recovery",
                description=(
                    "Backup, restore, reset, and snapshots."
                ),
                href="/teacher/recovery",
                css_class="teacher-card",
            ),
            tool_card(
                title="Configuration",
                description=(
                    "Inspect platform configuration."
                ),
                href="/teacher/configuration",
                css_class="teacher-card",
            ),
        ]
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>Betabox Launchpad</title>
    <link
        rel="stylesheet"
        href="/static/launchpad.css"
    >
</head>
<body>
    <header class="site-header">
        <div class="brand">
            <p class="eyebrow">Betabox Robotics</p>
            <h1>Launchpad</h1>

            <div class="robot-identity">
                <strong id="hud-hostname">Connecting…</strong>
                <span id="hud-ip"></span>
            </div>
        </div>

        <button
            id="hud-toggle"
            class="hud"
            type="button"
            aria-expanded="false"
            aria-controls="hud-details"
        >
            <span
                id="hud-health-dot"
                class="hud-health-dot status-unknown"
            ></span>

            <span class="hud-item hud-overall">
                <span class="hud-label">Robot</span>
                <strong id="hud-health">Checking…</strong>
            </span>

            <span class="hud-item">
                <span class="hud-label">Battery</span>
                <strong id="hud-battery">--</strong>
            </span>

            <span class="hud-item">
                <span class="hud-label">Temperature</span>
                <strong id="hud-temperature">--</strong>
            </span>

            <span class="hud-item hud-wide">
                <span class="hud-label">Camera</span>
                <strong id="hud-camera">--</strong>
            </span>

            <span class="hud-expand-icon" aria-hidden="true">
                ▾
            </span>
        </button>
    </header>

    <section
        id="hud-details"
        class="hud-details"
        hidden
    >
        <div class="hud-detail-grid">
            <div class="hud-detail">
                <span>Battery</span>
                <strong id="detail-battery">--</strong>
            </div>

            <div class="hud-detail">
                <span>CPU Temperature</span>
                <strong id="detail-temperature">--</strong>
            </div>

            <div class="hud-detail">
                <span>Memory</span>
                <strong id="detail-memory">--</strong>
            </div>

            <div class="hud-detail">
                <span>Disk</span>
                <strong id="detail-disk">--</strong>
            </div>

            <div class="hud-detail">
                <span>Camera</span>
                <strong id="detail-camera">--</strong>
            </div>

            <div class="hud-detail">
                <span>Vision</span>
                <strong id="detail-vision">--</strong>
            </div>

            <div class="hud-detail">
                <span>Audio</span>
                <strong id="detail-audio">--</strong>
            </div>

            <div class="hud-detail">
                <span>I²C</span>
                <strong id="detail-i2c">--</strong>
            </div>

        </div>

        <p id="hud-updated" class="hud-updated">
            Waiting for platform status…
        </p>
    </section>

    <main>
        <section>
            <div class="section-heading">
                <div>
                    <p class="eyebrow">Learn and Build</p>
                    <h2>Student Tools</h2>
                </div>
            </div>

            <div class="tool-grid">
                {student_tools}
            </div>
        </section>

        <section class="teacher-section">
            <div class="section-heading">
                <div>
                    <p class="eyebrow">Protected</p>
                    <h2>Teacher Tools</h2>
                </div>

                <button type="button">
                    Teacher Sign In
                </button>
            </div>

            <div class="tool-grid teacher-tools">
                {teacher_tools}
            </div>
        </section>
    </main>
    <script src="/static/launchpad.js"></script>
</body>
</html>
"""

    return web.Response(
        text=html,
        content_type="text/html",
    )


def setup_home_routes(
    app: web.Application,
) -> None:
    app.router.add_get("/", home)
