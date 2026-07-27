from __future__ import annotations

import json
import sys
from typing import Any

import pamela

from betabox_robotics.services.accounts import (
    account_by_username,
)


def read_request() -> tuple[str, str]:
    """Read and validate an authentication request from stdin."""

    try:
        payload: Any = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        raise ValueError("Invalid authentication request") from None

    if not isinstance(payload, dict):
        raise ValueError("Invalid authentication request")

    username = payload.get("username")
    password = payload.get("password")

    if not isinstance(username, str):
        raise ValueError("Invalid authentication request")

    if not isinstance(password, str):
        raise ValueError("Invalid authentication request")

    username = username.strip()

    if not username or not password:
        raise ValueError("Invalid authentication request")

    return username, password


def authenticate(
    username: str,
    password: str,
) -> bool:
    """Authenticate a managed persistent Launchpad account."""

    try:
        account = account_by_username(username)
    except LookupError:
        return False

    if not account.persistent:
        return False

    try:
        pamela.authenticate(
            account.username,
            password,
            service="login",
        )
    except pamela.PAMError:
        return False

    return True


def main() -> int:
    try:
        username, password = read_request()
    except ValueError:
        return 1

    if not authenticate(username, password):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
