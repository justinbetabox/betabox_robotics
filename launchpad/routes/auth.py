from __future__ import annotations

from urllib.parse import urlencode

from aiohttp import web

from betabox_robotics.launchpad.auth import (
    AUTHENTICATION_SERVICE_KEY,
    SESSION_COOKIE_NAME,
    SESSION_MANAGER_KEY,
    AuthenticationError,
)


def safe_return_to(
    value: str | None,
) -> str:
    """Return a safe local redirect target."""

    if value is None:
        return "/"

    value = value.strip()

    if not value:
        return "/"

    if not value.startswith("/"):
        return "/"

    if value.startswith("//"):
        return "/"

    if "\\" in value:
        return "/"

    return value


async def login(
    request: web.Request,
) -> web.StreamResponse:
    """Authenticate a student and create a Launchpad session."""

    form = await request.post()

    username = str(
        form.get(
            "username",
            "",
        )
    ).strip()

    password = str(
        form.get(
            "password",
            "",
        )
    )

    return_to = safe_return_to(
        str(
            form.get(
                "return_to",
                "/",
            )
        )
    )

    authentication_service = request.app[AUTHENTICATION_SERVICE_KEY]

    session_manager = request.app[SESSION_MANAGER_KEY]

    try:
        await authentication_service.authenticate(
            username,
            password,
        )

        session = session_manager.create(username)

    except (
        AuthenticationError,
        ValueError,
    ):
        query = urlencode(
            {
                "login": "failed",
            }
        )

        separator = "&" if "?" in return_to else "?"

        raise web.HTTPSeeOther(location=(f"{return_to}{separator}{query}"))

    assert session.id is not None

    response = web.HTTPSeeOther(location=return_to)

    response.set_cookie(
        SESSION_COOKIE_NAME,
        session.id,
        httponly=True,
        samesite="Lax",
        secure=False,
        path="/",
    )

    return response


async def logout(
    request: web.Request,
) -> web.StreamResponse:
    """Remove the current session and return to Guest."""

    form = await request.post()

    return_to = safe_return_to(
        str(
            form.get(
                "return_to",
                "/",
            )
        )
    )

    session_manager = request.app[SESSION_MANAGER_KEY]

    session_manager.remove_from_request(request)

    response = web.HTTPSeeOther(location=return_to)

    response.del_cookie(
        SESSION_COOKIE_NAME,
        path="/",
    )

    return response


def setup_auth_routes(
    app: web.Application,
) -> None:
    """Register authentication routes."""

    _ = app.router.add_post(
        "/login",
        login,
    )

    _ = app.router.add_post(
        "/logout",
        logout,
    )
