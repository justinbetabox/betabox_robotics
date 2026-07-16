from __future__ import annotations

from aiohttp import web


async def diagnostics_page(
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
        Diagnostics · Betabox Launchpad
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
        href="/static/diagnostics.css"
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
                Platform Health
            </p>

            <h1>
                Diagnostics
            </h1>
        </div>

        <div class="status-header-actions">
            <div
                id="diagnostics-connection"
                class="
                    status-connection
                    status-connecting
                "
                role="status"
                aria-live="polite"
            >
                Ready
            </div>

            <button
                id="run-diagnostics"
                class="button button-primary"
                type="button"
            >
                Run Diagnostics
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
                    id="diagnostics-updated"
                    class="status-updated"
                >
                    Diagnostics have not run yet.
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
                            Overall Result
                        </span>

                        <strong id="overall-status">
                            Not Run
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
                        Critical
                    </span>

                    <strong id="critical-count">
                        --
                    </strong>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Total Checks
                    </span>

                    <strong id="total-count">
                        --
                    </strong>
                </article>
            </div>
        </section>

        <section
            id="issues-section"
            class="
                status-section
                attention-section
            "
            aria-labelledby="issues-heading"
            hidden
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Review Recommended
                    </p>

                    <h2 id="issues-heading">
                        Issues Found
                    </h2>
                </div>

                <p
                    id="issues-summary"
                    class="status-updated"
                ></p>
            </div>

            <div
                id="issues-list"
                class="diagnostics-list"
            ></div>
        </section>

        <section
            class="status-section"
            aria-labelledby="results-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Platform Checks
                    </p>

                    <h2 id="results-heading">
                        Diagnostic Results
                    </h2>
                </div>

                <p class="status-updated">
                    Safe, read-only platform checks
                </p>
            </div>

            <div
                id="diagnostics-list"
                class="diagnostics-list"
            >
                <div class="diagnostics-empty">
                    <strong>
                        Ready to check the robot
                    </strong>

                    <p>
                        Run diagnostics to inspect platform
                        health, hardware, services, networking,
                        media paths, and classroom tools.
                    </p>
                </div>
            </div>
        </section>

        <section
            id="diagnostics-error-panel"
            class="status-error-panel"
            aria-labelledby="error-heading"
            hidden
        >
            <div>
                <p class="eyebrow">
                    Diagnostics Unavailable
                </p>

                <h2 id="error-heading">
                    Unable to run diagnostics
                </h2>

                <p id="diagnostics-error-message">
                    The diagnostics API did not respond.
                </p>
            </div>

            <button
                id="retry-diagnostics"
                class="button button-primary"
                type="button"
            >
                Try Again
            </button>
        </section>
    </main>

    <script src="/static/theme.js"></script>
    <script src="/static/diagnostics.js"></script>
</body>
</html>
"""

    return web.Response(
        text=html,
        content_type="text/html",
    )
