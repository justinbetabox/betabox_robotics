from __future__ import annotations

from collections.abc import Callable

from aiohttp import web

from .context import LaunchpadContext
from .permissions import Permission
from .provider import LAUNCHPAD_CONTEXT_KEY


def _validate_context(
    value: object,
) -> LaunchpadContext:
    if not isinstance(
        value,
        LaunchpadContext,
    ):
        raise TypeError("context must be a LaunchpadContext")

    return value


def _validate_permission_value(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("permission_value must be a string")

    result = value.strip()

    if not result:
        raise ValueError("permission_value cannot be empty")

    return result


def _validate_request(
    value: object,
) -> web.Request:
    if not isinstance(
        value,
        web.Request,
    ):
        raise TypeError("request must be a web.Request")

    return value


def build_permission_checker(
    context: LaunchpadContext,
) -> Callable[[str], bool]:
    """Build a permission-checking function for templates."""

    context_value = _validate_context(context)

    def can(
        permission_value: str,
    ) -> bool:
        """Return whether the current user has a permission."""

        permission_value_normalized = _validate_permission_value(permission_value)

        try:
            permission = Permission(permission_value_normalized)
        except ValueError as exc:
            raise ValueError(
                f"Unknown Launchpad permission: {permission_value_normalized!r}"
            ) from exc

        return context_value.can(permission)

    return can


async def launchpad_template_context(
    request: web.Request,
) -> dict[str, object]:
    """Build common template variables for a Launchpad request."""

    request_value = _validate_request(request)

    context = request_value[LAUNCHPAD_CONTEXT_KEY]

    if not isinstance(
        context,
        LaunchpadContext,
    ):
        raise TypeError("Launchpad context is invalid")

    return {
        "launchpad": context,
        "identity": context.identity,
        "is_guest": context.guest,
        "is_student": context.student,
        "is_teacher": context.teacher,
        "is_authenticated": (context.authenticated),
        "can": build_permission_checker(context),
        "login_failed": (request_value.query.get("login") == "failed"),
    }
