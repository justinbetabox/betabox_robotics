from __future__ import annotations

from aiohttp import web

from betabox_robotics.launchpad.components import (
    action_card,
)

def tool_card(
    *,
    title: str,
    description: str,
    href: str,
    category: str,
    accent: str = "blue",
    status: str | None = None,
    css_class: str = "",
) -> str:
    status_html = ""

    if status:
        status_html = f"""
        <span class="action-card-status">
            {escape(status)}
        </span>
        """

    return f"""
    <a
        class="
            action-card
            accent-{escape(accent)}
            {escape(css_class)}
        "
        href="{escape(href)}"
    >
        <span class="action-card-category">
            {escape(category)}
        </span>

        <h3>{escape(title)}</h3>

        <p>{escape(description)}</p>

        <div class="action-card-footer">
            {status_html}
            <span class="action-card-arrow" aria-hidden="true">
                →
            </span>
        </div>
    </a>
    """


async def home(
    request: web.Request,
) -> web.Response:

    student_tools = "".join(
        [
            action_card(
                title="Manual Drive",
                description=(
                    "Control movement, steering, and the camera "
                    "from your browser."
                ),
                href="/drive",
                category="Control",
                accent="blue",
                action="Open controls",
            ),
            action_card(
                title="Coding",
                description=(
                    "Open JupyterLab to write Python and "
                    "program your robot."
                ),
                href="/jupyter",
                category="Build",
                accent="green",
                action="Open JupyterLab",
            ),
            action_card(
                title="Live Camera",
                description=(
                    "View the robot's live camera feed."
                ),
                href="/camera",
                category="Vision",
                accent="orange",
                action="View camera",
            ),
            action_card(
                title="Media",
                description=(
                    "Browse pictures, videos, recordings, "
                    "and sounds."
                ),
                href="/media",
                category="Create",
                accent="pink",
                action="Browse media",
            ),
            action_card(
                title="Calibration",
                description=(
                    "Run guided calibration and hardware "
                    "alignment tools."
                ),
                href="/calibration",
                category="Setup",
                accent="blue",
                action="Calibrate robot",
            ),
        ]
    )

    information_tools = "".join(
        [
            action_card(
                title="Status",
                description=(
                    "See detailed robot, hardware, network, "
                    "and system health."
                ),
                href="/status",
                category="Understand",
                accent="blue",
                action="View status",
            ),
            action_card(
                title="Diagnostics",
                description=(
                    "Run Verify and Doctor to find and "
                    "understand problems."
                ),
                href="/diagnostics",
                category="Troubleshoot",
                accent="orange",
                action="Run checks",
            ),
            action_card(
                title="Services",
                description=(
                    "See which platform services are installed "
                    "and running."
                ),
                href="/services",
                category="Platform",
                accent="blue",
                action="View services",
            ),
            action_card(
                title="Configuration",
                description=(
                    "Explore the robot and platform "
                    "configuration safely."
                ),
                href="/configuration",
                category="Learn",
                accent="green",
                action="View configuration",
            ),
            action_card(
                title="Events",
                description=(
                    "Review recent robot and platform activity."
                ),
                href="/events",
                category="History",
                accent="pink",
                action="View events",
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
        href="/static/tokens.css"
    >
    <link
        rel="stylesheet"
        href="/static/components.css"
    >
    <link
        rel="stylesheet"
        href="/static/launchpad.css"
    >
</head>
<body class="launchpad-home">
    <header class="launchpad-header">
        <div class="launchpad-header-inner">
            <div class="brand">
                <p class="eyebrow">Betabox Robotics</p>
                <h1>Launchpad</h1>

                <div class="robot-identity">
                    <strong id="hud-hostname">Connecting…</strong>
                    <span id="hud-ip"></span>
                </div>
            </div>

            <div class="launchpad-header-actions">
                <button
                    id="theme-toggle"
                    class="theme-toggle"
                    type="button"
                >
                    Dark Mode
                </button>

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
                        <span class="hud-label">Control</span>
                        <strong id="hud-control">--</strong>
                    </span>

                    <span class="hud-item hud-wide">
                        <span class="hud-label">Camera</span>
                        <strong id="hud-camera">--</strong>
                    </span>

                    <span
                        class="hud-expand-icon"
                        aria-hidden="true"
                    >
                        ▾
                    </span>
                </button>
            </div>
        </div>

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
                    <span>Robot Control</span>
                    <strong id="detail-control">--</strong>
                </div>

                <div class="hud-detail">
                    <span>Network</span>
                    <strong id="detail-network">--</strong>
                </div>

                <div class="hud-detail">
                    <span>JupyterLab</span>
                    <strong id="detail-jupyter">--</strong>
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

            </div>

            <p id="hud-updated" class="hud-updated">
                Waiting for platform status…
            </p>
        </section>

    </header>

    <main class="page-content">
        <div class="content-container section-stack">
            <section>
                <div class="section-heading">
                    <div>
                        <p class="eyebrow">Learn and Build</p>
                        <h2 class="section-title">Use Your Robot</h2>
                    </div>
                </div>

                <div class="card-grid">
                    {student_tools}
                </div>
            </section>
            <section>
                <div class="section-heading">
                    <div>
                        <p class="eyebrow">Explore and Troubleshoot</p>
                        <h2 class="section-title">
                            Understand Your Robot
                        </h2>
                    </div>
                </div>

                <div class="card-grid">
                    {information_tools}
                </div>
            </section>
            <section class="admin-preview">
                <div>
                    <p class="eyebrow">Administrator</p>
                    <h2 class="section-title">
                        Platform Management
                    </h2>
                    <p>
                        Recovery, service controls, and configuration
                        editing require administrator access.
                    </p>
                </div>

                <button
                    class="button button-secondary"
                    type="button"
                >
                    Administrator Sign In
                </button>
            </section>
        </div>
    </main>

    <script src="/static/theme.js"></script>
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
