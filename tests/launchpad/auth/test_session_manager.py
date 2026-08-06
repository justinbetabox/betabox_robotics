from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from aiohttp import web
from betabox_robotics.launchpad.auth.session import Session
from betabox_robotics.launchpad.auth.session_manager import (
    SESSION_COOKIE_NAME,
    SESSION_MANAGER_KEY,
    SessionManager,
    _validate_request,
    _validate_session_id,
    _validate_username,
)

MODULE = "betabox_robotics.launchpad.auth.session_manager"


def make_account(
    *,
    username: str = "student1",
    persistent: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        username=username,
        persistent=persistent,
    )


def make_request(
    cookies: dict[str, str] | None = None,
) -> Mock:
    request = Mock()
    request.cookies = {} if cookies is None else cookies
    return request


class ValidationTests(unittest.TestCase):
    def test_validate_username_strips(
        self,
    ) -> None:
        self.assertEqual(
            _validate_username(" student1 "),
            "student1",
        )

    def test_validate_username_rejects_non_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "username must be a string",
        ):
            _validate_username(1)

    def test_validate_username_rejects_empty(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "username cannot be empty",
        ):
            _validate_username(" ")

    def test_validate_session_id_strips(
        self,
    ) -> None:
        self.assertEqual(
            _validate_session_id(" abc123 "),
            "abc123",
        )

    def test_validate_session_id_rejects_non_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "session_id must be a string",
        ):
            _validate_session_id(1)

    def test_validate_session_id_rejects_empty(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "session_id cannot be empty",
        ):
            _validate_session_id(" ")

    def test_validate_request_accepts_web_request(
        self,
    ) -> None:
        request = object.__new__(web.Request)

        self.assertIs(
            _validate_request(request),
            request,
        )

    def test_validate_request_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "request must be a web.Request",
        ):
            _validate_request(object())


class SessionManagerConstructionTests(unittest.TestCase):
    def test_starts_empty(
        self,
    ) -> None:
        manager = SessionManager()

        self.assertEqual(
            manager._sessions,
            {},
        )
        self.assertEqual(
            len(manager),
            0,
        )


class ResolveTests(unittest.TestCase):
    def test_returns_stored_session(
        self,
    ) -> None:
        manager = SessionManager()
        session = Session(
            id="abc123",
            username="student1",
        )
        manager._sessions["abc123"] = session
        request = make_request(
            {
                SESSION_COOKIE_NAME: "abc123",
            }
        )

        with patch(
            f"{MODULE}._validate_request",
            side_effect=lambda value: value,
        ):
            result = manager.resolve(
                request  # type: ignore[arg-type]
            )

        self.assertIs(
            result,
            session,
        )

    def test_missing_cookie_returns_guest(
        self,
    ) -> None:
        manager = SessionManager()

        with patch(
            f"{MODULE}._validate_request",
            side_effect=lambda value: value,
        ):
            result = manager.resolve(
                make_request()  # type: ignore[arg-type]
            )

        self.assertEqual(
            result,
            Session.guest(),
        )

    def test_unknown_cookie_returns_guest(
        self,
    ) -> None:
        manager = SessionManager()
        request = make_request(
            {
                SESSION_COOKIE_NAME: "missing",
            }
        )

        with patch(
            f"{MODULE}._validate_request",
            side_effect=lambda value: value,
        ):
            result = manager.resolve(
                request  # type: ignore[arg-type]
            )

        self.assertEqual(
            result,
            Session.guest(),
        )

    def test_empty_cookie_returns_guest(
        self,
    ) -> None:
        manager = SessionManager()
        request = make_request(
            {
                SESSION_COOKIE_NAME: "",
            }
        )

        with patch(
            f"{MODULE}._validate_request",
            side_effect=lambda value: value,
        ):
            result = manager.resolve(
                request  # type: ignore[arg-type]
            )

        self.assertEqual(
            result,
            Session.guest(),
        )

    def test_each_guest_resolution_returns_new_session(
        self,
    ) -> None:
        manager = SessionManager()
        request = make_request()

        with patch(
            f"{MODULE}._validate_request",
            side_effect=lambda value: value,
        ):
            first = manager.resolve(
                request  # type: ignore[arg-type]
            )
            second = manager.resolve(
                request  # type: ignore[arg-type]
            )

        self.assertEqual(
            first,
            second,
        )
        self.assertIsNot(
            first,
            second,
        )


class CreateTests(unittest.TestCase):
    def test_creates_and_stores_session(
        self,
    ) -> None:
        manager = SessionManager()
        account = make_account()
        session = Session(
            id="abc123",
            username="student1",
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ) as lookup,
            patch.object(
                Session,
                "for_username",
                return_value=session,
            ) as create_session,
        ):
            result = manager.create(" student1 ")

        self.assertIs(
            result,
            session,
        )
        lookup.assert_called_once_with("student1")
        create_session.assert_called_once_with("student1")
        self.assertIs(
            manager._sessions["abc123"],
            session,
        )
        self.assertEqual(
            len(manager),
            1,
        )

    def test_uses_canonical_account_username(
        self,
    ) -> None:
        manager = SessionManager()
        account = make_account(username="Student1")
        session = Session(
            id="abc123",
            username="Student1",
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ),
            patch.object(
                Session,
                "for_username",
                return_value=session,
            ) as create_session,
        ):
            manager.create("student1")

        create_session.assert_called_once_with("Student1")

    def test_rejects_nonpersistent_account(
        self,
    ) -> None:
        manager = SessionManager()

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(
                    username="guest",
                    persistent=False,
                ),
            ),
            patch.object(
                Session,
                "for_username",
            ) as create_session,
            self.assertRaisesRegex(
                ValueError,
                "Stored sessions require a persistent account",
            ),
        ):
            manager.create("guest")

        create_session.assert_not_called()
        self.assertEqual(
            len(manager),
            0,
        )

    def test_account_lookup_error_propagates(
        self,
    ) -> None:
        manager = SessionManager()
        error = LookupError("missing")

        with (
            patch(
                f"{MODULE}.account_by_username",
                side_effect=error,
            ),
            self.assertRaises(LookupError) as context,
        ):
            manager.create("missing")

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_username(
        self,
    ) -> None:
        manager = SessionManager()

        with (
            patch(f"{MODULE}.account_by_username") as lookup,
            self.assertRaisesRegex(
                ValueError,
                "username cannot be empty",
            ),
        ):
            manager.create(" ")

        lookup.assert_not_called()

    def test_rejects_session_without_id(
        self,
    ) -> None:
        manager = SessionManager()
        guest_session = Session.guest()

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            patch.object(
                Session,
                "for_username",
                return_value=guest_session,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "stored session did not receive an ID",
            ),
        ):
            manager.create("student1")

        self.assertEqual(
            len(manager),
            0,
        )

    def test_new_session_with_same_id_replaces_existing(
        self,
    ) -> None:
        manager = SessionManager()
        first = Session(
            id="abc123",
            username="student1",
        )
        second = Session(
            id="abc123",
            username="student2",
        )
        manager._sessions["abc123"] = first

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(username="student2"),
            ),
            patch.object(
                Session,
                "for_username",
                return_value=second,
            ),
        ):
            manager.create("student2")

        self.assertIs(
            manager._sessions["abc123"],
            second,
        )
        self.assertEqual(
            len(manager),
            1,
        )


class RemoveTests(unittest.TestCase):
    def test_removes_existing_session(
        self,
    ) -> None:
        manager = SessionManager()
        manager._sessions["abc123"] = Session(
            id="abc123",
            username="student1",
        )

        manager.remove(" abc123 ")

        self.assertEqual(
            len(manager),
            0,
        )

    def test_missing_session_is_ignored(
        self,
    ) -> None:
        manager = SessionManager()

        self.assertIsNone(manager.remove("missing"))
        self.assertEqual(
            len(manager),
            0,
        )

    def test_rejects_invalid_session_id(
        self,
    ) -> None:
        manager = SessionManager()

        with self.assertRaisesRegex(
            ValueError,
            "session_id cannot be empty",
        ):
            manager.remove(" ")


class RemoveFromRequestTests(unittest.TestCase):
    def test_removes_cookie_session(
        self,
    ) -> None:
        manager = SessionManager()
        manager._sessions["abc123"] = Session(
            id="abc123",
            username="student1",
        )
        request = make_request(
            {
                SESSION_COOKIE_NAME: "abc123",
            }
        )

        with patch(
            f"{MODULE}._validate_request",
            side_effect=lambda value: value,
        ):
            manager.remove_from_request(
                request  # type: ignore[arg-type]
            )

        self.assertEqual(
            len(manager),
            0,
        )

    def test_missing_cookie_does_nothing(
        self,
    ) -> None:
        manager = SessionManager()

        with (
            patch.object(
                manager,
                "remove",
            ) as remove,
            patch(
                f"{MODULE}._validate_request",
                side_effect=lambda value: value,
            ),
        ):
            manager.remove_from_request(
                make_request()  # type: ignore[arg-type]
            )

        remove.assert_not_called()

    def test_empty_cookie_does_nothing(
        self,
    ) -> None:
        manager = SessionManager()

        with (
            patch.object(
                manager,
                "remove",
            ) as remove,
            patch(
                f"{MODULE}._validate_request",
                side_effect=lambda value: value,
            ),
        ):
            manager.remove_from_request(
                make_request(
                    {
                        SESSION_COOKIE_NAME: "",
                    }
                )  # type: ignore[arg-type]
            )

        remove.assert_not_called()

    def test_passes_cookie_to_remove(
        self,
    ) -> None:
        manager = SessionManager()
        request = make_request(
            {
                SESSION_COOKIE_NAME: "abc123",
            }
        )

        with (
            patch.object(
                manager,
                "remove",
            ) as remove,
            patch(
                f"{MODULE}._validate_request",
                side_effect=lambda value: value,
            ),
        ):
            manager.remove_from_request(
                request  # type: ignore[arg-type]
            )

        remove.assert_called_once_with("abc123")


class ClearAndLengthTests(unittest.TestCase):
    def test_length_tracks_sessions(
        self,
    ) -> None:
        manager = SessionManager()

        self.assertEqual(
            len(manager),
            0,
        )

        manager._sessions["one"] = Session(
            id="one",
            username="student1",
        )
        manager._sessions["two"] = Session(
            id="two",
            username="student2",
        )

        self.assertEqual(
            len(manager),
            2,
        )

    def test_clear_removes_every_session(
        self,
    ) -> None:
        manager = SessionManager()
        manager._sessions["one"] = Session(
            id="one",
            username="student1",
        )
        manager._sessions["two"] = Session(
            id="two",
            username="student2",
        )

        self.assertIsNone(manager.clear())
        self.assertEqual(
            len(manager),
            0,
        )


class SessionManagerKeyTests(unittest.TestCase):
    def test_cookie_name(
        self,
    ) -> None:
        self.assertEqual(
            SESSION_COOKIE_NAME,
            "betabox_session",
        )

    def test_key_is_app_key(
        self,
    ) -> None:
        self.assertIsInstance(
            SESSION_MANAGER_KEY,
            web.AppKey,
        )

    def test_key_can_store_and_retrieve_manager(
        self,
    ) -> None:
        app = web.Application()
        manager = SessionManager()

        app[SESSION_MANAGER_KEY] = manager

        self.assertIs(
            app[SESSION_MANAGER_KEY],
            manager,
        )


if __name__ == "__main__":
    unittest.main()
