from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import cast

from aiohttp import web

from betabox_robotics.services.accounts import (
    account_by_username,
)

AUTH_HELPER = Path("/opt/betabox/venv/bin/betabox-auth-check")

AuthRunner = Callable[
    [str, str],
    Awaitable[bool],
]


def _validate_string(
    value: object,
    *,
    name: str,
    strip: bool = True,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip() if strip else value

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_auth_runner(
    value: object,
) -> AuthRunner:
    if not callable(value):
        raise TypeError("authenticate must be callable")

    return cast(
        AuthRunner,
        value,
    )


class AuthenticationError(Exception):
    """Raised when Launchpad authentication cannot be completed."""


class AuthenticationService:
    """Authenticate persistent managed Launchpad accounts."""

    def __init__(
        self,
        authenticate: AuthRunner | None = None,
    ) -> None:
        self._authenticate = (
            self._authenticate_with_helper
            if authenticate is None
            else _validate_auth_runner(authenticate)
        )

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> None:
        """Authenticate a persistent managed account."""

        try:
            username_value = _validate_string(
                username,
                name="username",
            )
            password_value = _validate_string(
                password,
                name="password",
                strip=False,
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise AuthenticationError("Username and password are required.") from exc

        try:
            account = account_by_username(username_value)
        except LookupError as exc:
            raise AuthenticationError("Invalid username or password.") from exc

        if not account.persistent:
            raise AuthenticationError("Invalid username or password.")

        try:
            authenticated = await self._authenticate(
                account.username,
                password_value,
            )
        except asyncio.CancelledError:
            raise
        except (
            OSError,
            RuntimeError,
        ) as exc:
            raise AuthenticationError("Authentication service is unavailable.") from exc

        if not isinstance(
            authenticated,
            bool,
        ):
            raise TypeError("authentication runner must return a boolean")

        if not authenticated:
            raise AuthenticationError("Invalid username or password.")

    @staticmethod
    async def _authenticate_with_helper(
        username: str,
        password: str,
    ) -> bool:
        """Authenticate credentials through the privileged helper."""

        username_value = _validate_string(
            username,
            name="username",
        )
        password_value = _validate_string(
            password,
            name="password",
            strip=False,
        )

        if not AUTH_HELPER.is_file():
            raise RuntimeError(f"authentication helper not found: {AUTH_HELPER}")

        payload = json.dumps(
            {
                "username": username_value,
                "password": password_value,
            },
            separators=(
                ",",
                ":",
            ),
        ).encode("utf-8")

        process = await asyncio.create_subprocess_exec(
            "sudo",
            "-n",
            str(AUTH_HELPER),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        try:
            await process.communicate(payload)
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
                await process.wait()

            raise

        return process.returncode == 0


AUTHENTICATION_SERVICE_KEY = web.AppKey(
    "launchpad_authentication_service",
    AuthenticationService,
)
