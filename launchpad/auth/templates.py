from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aiohttp import web

from .context import LaunchpadContext
from .permissions import Permission
from .provider import LAUNCHPAD_CONTEXT_KEY


def build_permission_checker(
    context: LaunchpadContext,
) -> Callable[[str], bool]:
    """Build a permission-checking function for templates."""

    def can(permission_value: str) -> bool:
        """Return whether the current user has a permission."""

        try:
            permission = Permission(permission_value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown Launchpad permission: {permission_value!r}"
            ) from exc

        return context.can(permission)

    return can


async def launchpad_template_context(
    request: web.Request,
) -> dict[str, Any]:
    """Expose the current Launchpad context to Jinja templates."""

    context = request[LAUNCHPAD_CONTEXT_KEY]

    return {
        "launchpad": context,
        "identity": context.identity,
        "workspace": context.workspace,
        "permissions": context.permissions,
        "can": build_permission_checker(context),
        "is_guest": context.guest,
        "is_student": context.student,
        "is_teacher": context.teacher,
        "is_authenticated": context.authenticated,
    }
