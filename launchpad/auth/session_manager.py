from __future__ import annotations

from aiohttp import web

from betabox_robotics.services.accounts import (
    account_by_username,
)

from .session import Session

SESSION_COOKIE_NAME = "betabox_session"


def _validate_request(
    value: object,
) -> web.Request:
    if not isinstance(
        value,
        web.Request,
    ):
        raise TypeError("request must be a web.Request")

    return value


def _validate_session_id(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("session_id must be a string")

    result = value.strip()

    if not result:
        raise ValueError("session_id cannot be empty")

    return result


def _validate_username(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("username must be a string")

    result = value.strip()

    if not result:
        raise ValueError("username cannot be empty")

    return result


class SessionManager:
    """Resolve and manage Launchpad browser sessions."""

    def __init__(
        self,
    ) -> None:
        self._sessions: dict[
            str,
            Session,
        ] = {}

    def resolve(
        self,
        request: web.Request,
    ) -> Session:
        """Resolve the current session or return the guest session."""

        request_value = _validate_request(request)

        session_id = request_value.cookies.get(SESSION_COOKIE_NAME)

        if session_id:
            session = self._sessions.get(session_id)

            if session is not None:
                return session

        return Session.guest()

    def create(
        self,
        username: str,
    ) -> Session:
        """Create and store a session for a managed account."""

        username_value = _validate_username(username)

        account = account_by_username(username_value)

        if not account.persistent:
            raise ValueError("Stored sessions require a persistent account")

        session = Session.for_username(account.username)

        session_id = session.id

        if session_id is None:
            raise RuntimeError("stored session did not receive an ID")

        self._sessions[session_id] = session

        return session

    def remove(
        self,
        session_id: str,
    ) -> None:
        """Remove a stored session."""

        session_id_value = _validate_session_id(session_id)

        self._sessions.pop(
            session_id_value,
            None,
        )

    def remove_from_request(
        self,
        request: web.Request,
    ) -> None:
        """Remove the session referenced by the request cookie."""

        request_value = _validate_request(request)

        session_id = request_value.cookies.get(SESSION_COOKIE_NAME)

        if session_id:
            self.remove(session_id)

    def clear(
        self,
    ) -> None:
        """Remove every stored session."""

        self._sessions.clear()

    def __len__(
        self,
    ) -> int:
        return len(self._sessions)


SESSION_MANAGER_KEY = web.AppKey(
    "launchpad_session_manager",
    SessionManager,
)
