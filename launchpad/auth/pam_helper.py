from __future__ import annotations

import json
import sys
from typing import Protocol, cast

import pamela  # pyright: ignore[reportMissingTypeStubs]

from betabox_robotics.services.accounts import (
    account_by_username,
)


class PamAuthenticate(Protocol):
    def __call__(
        self,
        username: str,
        password: str,
        *,
        service: str = "login",
    ) -> object: ...


def _validate_string(
    value: object,
    *,
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


def _pam_authenticate(
    username: str,
    password: str,
) -> None:
    authenticate = cast(
        PamAuthenticate,
        pamela.authenticate,
    )

    _ = authenticate(
        username,
        password,
        service="login",
    )


def read_request() -> tuple[str, str]:
    """Read and validate an authentication request from stdin."""

    try:
        payload = cast(
            object,
            json.load(sys.stdin),
        )
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

    request = cast(
        dict[object, object],
        payload,
    )

    username: str = _validate_string(
        request.get("username"),
    )

    password: str = _validate_string(
        request.get("password"),
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
        )

        password_value = _validate_string(
            password,
            strip=False,
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    try:
        account = account_by_username(username_value)
    except LookupError:
        return False

    if not account.persistent:
        return False

    try:
        _pam_authenticate(
            account.username,
            password_value,
        )
    except pamela.PAMError:
        return False

    return True


def main() -> int:
    try:
        username, password = read_request()
    except (
        TypeError,
        ValueError,
    ):
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
