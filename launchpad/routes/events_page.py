from __future__ import annotations

from aiohttp import web


async def events_page(
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
        Events · Betabox Launchpad
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
        href="/static/events.css"
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
                Platform Activity
            </p>

            <h1>
                Events
            </h1>
        </div>

        <div class="status-header-actions">
            <div
                id="events-connection"
                class="
                    status-connection
                    status-connecting
                "
                role="status"
                aria-live="polite"
            >
                Loading…
            </div>

            <button
                id="refresh-events"
                class="button button-primary"
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
                        Recent Activity
                    </p>

                    <h2 id="overview-heading">
                        Overview
                    </h2>
                </div>

                <p
                    id="events-updated"
                    class="status-updated"
                >
                    Loading platform events…
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
                        class="
                            status-indicator
                            status-unknown
                        "
                        aria-hidden="true"
                    ></span>

                    <div>
                        <span class="overview-label">
                            Events Shown
                        </span>

                        <strong id="total-count">
                            --
                        </strong>
                    </div>
                </article>

                <article class="overview-card">
                    <span class="overview-label">
                        Information
                    </span>

                    <strong id="info-count">
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
                        Matching Events
                    </span>

                    <strong id="available-count">
                        --
                    </strong>
                </article>
            </div>
        </section>

        <section
            class="status-section"
            aria-labelledby="filters-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Event Filters
                    </p>

                    <h2 id="filters-heading">
                        Filter Activity
                    </h2>
                </div>

                <button
                    id="clear-filters"
                    class="button button-secondary"
                    type="button"
                >
                    Clear Filters
                </button>
            </div>

            <form
                id="events-filter-form"
                class="events-filter-form"
            >
                <label class="events-filter-field">
                    <span>
                        Severity
                    </span>

                    <select id="severity-filter">
                        <option value="">
                            All severities
                        </option>

                        <option value="info">
                            Information
                        </option>

                        <option value="warning">
                            Warning
                        </option>

                        <option value="error">
                            Error
                        </option>

                        <option value="critical">
                            Critical
                        </option>
                    </select>
                </label>

                <label class="events-filter-field">
                    <span>
                        Component
                    </span>

                    <select id="component-filter">
                        <option value="">
                            All components
                        </option>
                    </select>
                </label>

                <label class="events-filter-field">
                    <span>
                        Number of events
                    </span>

                    <select id="limit-filter">
                        <option value="25">
                            25
                        </option>

                        <option value="50" selected>
                            50
                        </option>

                        <option value="100">
                            100
                        </option>

                        <option value="250">
                            250
                        </option>
                    </select>
                </label>

                <div class="events-filter-action">
                    <button
                        class="button button-primary"
                        type="submit"
                    >
                        Apply Filters
                    </button>
                </div>
            </form>
        </section>

        <section
            class="status-section"
            aria-labelledby="events-heading"
        >
            <div class="section-heading">
                <div>
                    <p class="eyebrow">
                        Newest First
                    </p>

                    <h2 id="events-heading">
                        Platform Events
                    </h2>
                </div>

                <p
                    id="event-list-summary"
                    class="status-updated"
                >
                    Loading…
                </p>
            </div>

            <div
                id="events-list"
                class="events-list"
                aria-live="polite"
            >
                <div class="events-empty">
                    Loading platform events…
                </div>
            </div>
        </section>

        <section
            id="events-error-panel"
            class="status-error-panel"
            aria-labelledby="error-heading"
            hidden
        >
            <div>
                <p class="eyebrow">
                    Events Unavailable
                </p>

                <h2 id="error-heading">
                    Unable to load events
                </h2>

                <p id="events-error-message">
                    The Events API did not respond.
                </p>
            </div>

            <button
                id="retry-events"
                class="button button-primary"
                type="button"
            >
                Try Again
            </button>
        </section>
    </main>

    <script src="/static/theme.js"></script>
    <script src="/static/events.js"></script>
</body>
</html>
"""

    return web.Response(
        text=html,
        content_type="text/html",
    )
