from __future__ import annotations

import json
import sys

import pamela

from betabox_robotics.services.accounts import (
    account_by_username,
)


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
        raise TypeError("Invalid authentication request")

    result = value.strip() if strip else value

    if not result:
        raise ValueError("Invalid authentication request")

    return result


def read_request() -> tuple[str, str]:
    """Read and validate an authentication request from stdin."""

    try:
        payload: object = json.load(sys.stdin)
    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
        UnicodeError,
    ):
        raise ValueError("Invalid authentication request") from None

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError("Invalid authentication request")

    username = _validate_string(
        payload.get("username"),
        name="username",
    )
    password = _validate_string(
        payload.get("password"),
        name="password",
        strip=False,
    )

    return (
        username,
        password,
    )


def authenticate(
    username: str,
    password: str,
) -> bool:
    """Authenticate a managed persistent Launchpad account."""

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
    except (TypeError, ValueError):
        return False

    try:
        account = account_by_username(username_value)
    except LookupError:
        return False

    if not account.persistent:
        return False

    try:
        pamela.authenticate(
            account.username,
            password_value,
            service="login",
        )
    except pamela.PAMError:
        return False

    return True


def main() -> int:
    try:
        username, password = read_request()
    except (TypeError, ValueError):
        return 1

    return (
        0
        if authenticate(
            username,
            password,
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
