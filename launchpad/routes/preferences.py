from __future__ import annotations

import json

from aiohttp import web

from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LaunchpadContext,
    Permission,
)
from betabox_robotics.launchpad.preferences import (
    read_preferences,
    reset_preferences,
    validate_preferences,
    write_preferences,
)


def preferences_context(
    request: web.Request,
) -> LaunchpadContext:
    context: LaunchpadContext = request[LAUNCHPAD_CONTEXT_KEY]

    context.require(Permission.PREFERENCES)

    return context


async def preferences_api(
    request: web.Request,
) -> web.Response:
    """Return preferences for the current Launchpad workspace."""

    context = preferences_context(request)

    try:
        preferences = read_preferences(context.workspace.preferences)
    except json.JSONDecodeError as exc:
        return web.json_response(
            {
                "error": "preferences_invalid",
                "message": "Stored Launchpad preferences are invalid.",
                "detail": str(exc),
            },
            status=500,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        return web.json_response(
            {
                "error": "preferences_invalid",
                "message": "Stored Launchpad preferences are invalid.",
                "detail": str(exc),
            },
            status=500,
        )
    except OSError as exc:
        return web.json_response(
            {
                "error": "preferences_unavailable",
                "message": "Unable to load Launchpad preferences.",
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(preferences)


async def update_preferences_api(
    request: web.Request,
) -> web.Response:
    """Update preferences for the current Launchpad workspace."""

    context = preferences_context(request)

    try:
        payload = await request.json()

    except (
        TypeError,
        ValueError,
    ):
        return web.json_response(
            {
                "error": "invalid_request",
                "message": "Preferences must be valid JSON.",
            },
            status=400,
        )

    try:
        preferences = validate_preferences(payload)

    except (
        TypeError,
        ValueError,
    ) as exc:
        return web.json_response(
            {
                "error": "invalid_preferences",
                "message": str(exc),
            },
            status=400,
        )

    try:
        saved = write_preferences(
            context.workspace.preferences,
            preferences,
        )

    except OSError as exc:
        return web.json_response(
            {
                "error": "preferences_unavailable",
                "message": "Unable to save Launchpad preferences.",
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(saved)


async def reset_preferences_api(
    request: web.Request,
) -> web.Response:
    """Reset preferences for the current Launchpad workspace."""

    context = preferences_context(request)

    try:
        preferences = reset_preferences(context.workspace.preferences)
    except OSError as exc:
        return web.json_response(
            {
                "error": "preferences_unavailable",
                "message": "Unable to reset Launchpad preferences.",
                "detail": str(exc),
            },
            status=500,
        )

    return web.json_response(preferences)


def setup_preferences_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/api/preferences",
        preferences_api,
        name="preferences-api",
    )

    app.router.add_put(
        "/api/preferences",
        update_preferences_api,
        name="preferences-update-api",
    )

    app.router.add_delete(
        "/api/preferences",
        reset_preferences_api,
        name="preferences-reset-api",
    )
