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
                href=config.network.jupyterhub_url,
            ),
            tool_card(
                title="Live Camera",
                description=(
                    "View the robot camera stream."
                ),
                href=config.network.vision_url,
            ),
            tool_card(
                title="Media",
                description=(
                    "Browse pictures, videos, and sounds."
                ),
                href="/media",
            ),
            tool_card(
                title="Robot Status",
                description=(
                    "Check battery, sensors, and platform health."
                ),
                href="/status",
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
        <div>
            <p class="eyebrow">Betabox Robotics</p>
            <h1>Launchpad</h1>
            <p class="subtitle">
                Choose a tool to begin.
            </p>
        </div>

        <div class="role-badge">
            Student Mode
        </div>
    </header>

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
