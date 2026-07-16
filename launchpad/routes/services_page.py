from __future__ import annotations

from aiohttp import web


async def services_page(
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
        Services · Betabox Launchpad
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

    <link
        rel="stylesheet"
        href="/static/services.css"
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
                Platform Services
            </p>

            <h1>
                Services
            </h1>
        </div>

        <div class="status-header-actions">
            <div
                id="services-connection"
                class="
                    status-connection
                    status-connecting
                "
                role="status"
                aria-live="polite"
            >
                Connecting…
            </div>

            <button
                id="refresh-services"
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
                    id="services-updated"
                    class="status-updated"
                >
                    Waiting for service status…
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
                            Overall Status
                        </span>

                        <strong id="overall-status">
                            Checking…
                        </strong>
                    </div>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Healthy
                    </span>

                    <strong id="healthy-count">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Warnings
                    </span>

                    <strong id="warning-count">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Errors
                    </span>

                    <strong id="error-count">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Unknown
                    </span>

                    <strong id="unknown-count">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Total Services
                    </span>

                    <strong id="total-count">
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
            aria-labelledby="services-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Robot Platform
                    </p>

                    <h2 id="services-heading">
                        Platform Services
                    </h2>
                </div>

                <p class="status-updated">
                These services provide the core features of your robot.
                </p>
            </div>

            <div
                id="services-list"
                class="services-grid"
            >
                <p class="status-placeholder">
                    Loading platform services…
                </p>
            </div>
        </section>

        <section
            id="services-error-panel"
            class="status-error-panel"
            aria-labelledby="error-heading"
            hidden
        >
            <div>
                <p class="eyebrow">
                    Services Unavailable
                </p>

                <h2 id="error-heading">
                    Unable to load platform services
                </h2>

                <p id="services-error-message">
                    The services API did not respond.
                </p>
            </div>

            <button
                id="retry-services"
                class="button button-primary"
                type="button"
            >
                Try Again
            </button>
        </section>
    </main>

    <script src="/static/theme.js"></script>
    <script src="/static/services.js"></script>
</body>
</html>
"""

    return web.Response(
        text=html,
        content_type="text/html",
    )
