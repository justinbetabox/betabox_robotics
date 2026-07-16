from __future__ import annotations

from aiohttp import web


async def detailed_status_page(
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

    <title>
        Robot Status · Betabox Launchpad
    </title>

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
        href="/static/detailed_status.css"
    >
</head>

<body class="status-body">
    <header class="status-header">
        <a
            class="back-link"
            href="/"
        >
            ← Launchpad
        </a>

        <div class="status-header-title">
            <p class="eyebrow">
                Platform Diagnostics
            </p>

            <h1>
                Robot Status
            </h1>
        </div>

        <div class="status-header-actions">
            <div
                id="status-connection"
                class="status-connection status-connecting"
                role="status"
                aria-live="polite"
            >
                Connecting…
            </div>

            <button
                id="refresh-status"
                class="button button-secondary"
                type="button"
            >
                Refresh
            </button>
        </div>
    </header>

    <main class="status-layout">
        <section
            class="status-overview"
            aria-labelledby="overview-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Current Condition
                    </p>

                    <h2 id="overview-heading">
                        Overview
                    </h2>
                </div>

                <p
                    id="status-updated"
                    class="status-updated"
                >
                    Waiting for platform status…
                </p>
            </div>

            <div class="overview-grid">
                <article
                    class="
                        overview-card
                        overview-card-primary
                    "
                >
                    <span
                        id="overall-indicator"
                        class="
                            status-indicator
                            status-unknown
                        "
                        aria-hidden="true"
                    ></span>

                    <div>
                        <span class="overview-label">
                            Overall Health
                        </span>

                        <strong id="overall-status">
                            Checking…
                        </strong>
                    </div>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Battery
                    </span>

                    <strong id="battery-status">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        CPU Temperature
                    </span>

                    <strong id="temperature-status">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Robot Control
                    </span>

                    <strong id="robot-status">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Camera
                    </span>

                    <strong id="vision-status">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        JupyterHub
                    </span>

                    <strong id="audio-status">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Services
                    </span>

                    <strong id="services-status">
                        --
                    </strong>
                </article>
            </div>
        </section>

        <section
            id="attention-section"
            class="
                status-section
                attention-section
            "
            aria-labelledby="attention-heading"
            hidden
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Action Required
                    </p>

                    <h2 id="attention-heading">
                        Needs Attention
                    </h2>
                </div>
            </div>

            <div
                id="attention-list"
                class="attention-list"
            ></div>
        </section>

        <section
            class="status-section"
            aria-labelledby="hardware-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Robot
                    </p>

                    <h2 id="hardware-heading">
                        Hardware and Control
                    </h2>
                </div>
            </div>

            <div
                id="hardware-status"
                class="detail-grid"
            >
                <p class="status-placeholder">
                    Loading hardware information…
                </p>
            </div>
        </section>

        <section
            class="status-section"
            aria-labelledby="system-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Raspberry Pi
                    </p>

                    <h2 id="system-heading">
                        System Resources
                    </h2>
                </div>
            </div>

            <div
                id="system-status"
                class="detail-grid"
            >
                <p class="status-placeholder">
                    Loading system information…
                </p>
            </div>
        </section>

        <section
            class="status-section"
            aria-labelledby="network-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Connectivity
                    </p>

                    <h2 id="network-heading">
                        Network
                    </h2>
                </div>
            </div>

            <div
                id="network-status"
                class="detail-grid"
            >
                <p class="status-placeholder">
                    Loading network information…
                </p>
            </div>
        </section>

        <section
            id="status-error-panel"
            class="status-error-panel"
            aria-labelledby="error-heading"
            hidden
        >
            <div>
                <p class="eyebrow">
                    Status Unavailable
                </p>

                <h2 id="error-heading">
                    Unable to load platform status
                </h2>

                <p id="status-error-message">
                    The status API did not respond.
                </p>
            </div>

            <button
                id="retry-status"
                class="button button-primary"
                type="button"
            >
                Try Again
            </button>
        </section>
    </main>

    <script src="/static/theme.js"></script>
    <script src="/static/detailed_status.js"></script>
</body>
</html>
"""

    return web.Response(
        text=html,
        content_type="text/html",
    )
