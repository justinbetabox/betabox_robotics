from __future__ import annotations

from aiohttp import web

from betabox_robotics.services.accounts import (
    account_by_username,
)

from .session import Session

SESSION_COOKIE_NAME = "betabox_session"


class SessionManager:
    """Resolve and manage Launchpad browser sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def resolve(
        self,
        request: web.Request,
    ) -> Session:
        """Resolve the current session or return the guest identity."""

        session_id = request.cookies.get(SESSION_COOKIE_NAME)

        if session_id is not None:
            session = self._sessions.get(session_id)

            if session is not None:
                return session

        return Session.guest()

    def create(
        self,
        username: str,
    ) -> Session:
        """Create and store a session for a managed account."""

        account = account_by_username(username)

        if not account.persistent:
            raise ValueError("Stored sessions require a persistent account")

        session = Session.for_username(account.username)

        assert session.id is not None

        self._sessions[session.id] = session

        return session

    def remove(
        self,
        session_id: str,
    ) -> None:
        """Remove a stored session."""

        self._sessions.pop(
            session_id,
            None,
        )

    def remove_from_request(
        self,
        request: web.Request,
    ) -> None:
        """Remove the session referenced by the request cookie."""

        session_id = request.cookies.get(SESSION_COOKIE_NAME)

        if session_id is not None:
            self.remove(session_id)


SESSION_MANAGER_KEY = web.AppKey(
    "launchpad_session_manager",
    SessionManager,
)
