from __future__ import annotations

import asyncio

from aiohttp import web

from betabox_robotics.config import (
    PlatformConfig,
)
from betabox_robotics.launchpad.routes.events_page import (
    events_page,
)
from betabox_robotics.services.events import (
    collect_event_report,
)


def parse_last(
    request: web.Request,
    default: int,
) -> int:
    """
    Parse the optional event limit from the query string.
    """

    raw_value = request.query.get(
        "last"
    )

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise web.HTTPBadRequest(
            text="last must be an integer"
        ) from exc

    if value < 0:
        raise web.HTTPBadRequest(
            text="last cannot be negative"
        )

    return value


def parse_optional_filter(
    request: web.Request,
    name: str,
) -> str | None:
    """
    Return a trimmed optional query-string filter.
    """

    value = request.query.get(
        name
    )

    if value is None:
        return None

    value = value.strip()

    return value or None


async def events_api(
    request: web.Request,
) -> web.Response:
    """
    Return recent platform events.

    The endpoint is read-only and supports optional filters:

    - ``last``
    - ``severity``
    - ``component``
    """

    config: PlatformConfig = request.app[
        "platform_config"
    ]

    last = parse_last(
        request,
        config.monitoring.default_event_count,
    )

    severity = parse_optional_filter(
        request,
        "severity",
    )

    component = parse_optional_filter(
        request,
        "component",
    )

    allowed_severities = {
        "info",
        "warning",
        "error",
        "critical",
    }

    if (
        severity is not None
        and severity.lower()
        not in allowed_severities
    ):
        raise web.HTTPBadRequest(
            text=(
                "severity must be one of: "
                "info, warning, error, critical"
            )
        )

    try:
        report = await asyncio.to_thread(
            collect_event_report,
            last=last,
            severity=severity,
            component=component,
            config=config,
        )
    except ValueError as exc:
        return web.json_response(
            {
                "error": "invalid_event_request",
                "message": str(exc),
            },
            status=400,
        )
    except Exception as exc:
        return web.json_response(
            {
                "error": "events_unavailable",
                "message": (
                    "Unable to load platform events."
                ),
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(
        report.to_dict()
    )


def setup_events_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/events",
        events_page,
    )

    app.router.add_get(
        "/api/events",
        events_api,
    )
