from __future__ import annotations

from typing import Any

from aiohttp import web

from .context import LaunchpadContext


async def launchpad_template_context(
    request: web.Request,
) -> dict[str, Any]:
    """Expose the current Launchpad context to Jinja templates."""

    context: LaunchpadContext = request["launchpad_context"]

    return {
        "launchpad": context,
        "identity": context.identity,
        "workspace": context.workspace,
        "permissions": context.permissions,
        "is_guest": context.guest,
        "is_authenticated": context.identity.authenticated,
    }
