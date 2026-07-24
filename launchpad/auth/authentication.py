from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from aiohttp import web

from betabox_robotics.services.workspace import (
    account_by_username,
)

AUTH_HELPER = "/opt/betabox/venv/bin/betabox-auth-check"

AuthRunner = Callable[
    [str, str],
    Awaitable[bool],
]


class AuthenticationError(Exception):
    """Raised when Launchpad credentials are invalid."""


class AuthenticationService:
    """Authenticate managed Launchpad student accounts."""

    def __init__(
        self,
        authenticate: AuthRunner | None = None,
    ) -> None:
        self._authenticate = (
            authenticate if authenticate is not None else self._authenticate_with_helper
        )

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> None:
        """Authenticate a persistent managed account."""

        normalized_username = username.strip()

        if not normalized_username or not password:
            raise AuthenticationError("Username and password are required.")

        try:
            account = account_by_username(normalized_username)
        except LookupError as error:
            raise AuthenticationError("Invalid username or password.") from error

        if not account.persistent:
            raise AuthenticationError("Invalid username or password.")

        authenticated = await self._authenticate(
            account.username,
            password,
        )

        if not authenticated:
            raise AuthenticationError("Invalid username or password.")

    @staticmethod
    async def _authenticate_with_helper(
        username: str,
        password: str,
    ) -> bool:
        """Authenticate credentials through the privileged helper."""

        payload = json.dumps(
            {
                "username": username,
                "password": password,
            }
        ).encode()

        process = await asyncio.create_subprocess_exec(
            "sudo",
            "-n",
            AUTH_HELPER,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        await process.communicate(payload)

        return process.returncode == 0


AUTHENTICATION_SERVICE_KEY = web.AppKey(
    "launchpad_authentication_service",
    AuthenticationService,
)
