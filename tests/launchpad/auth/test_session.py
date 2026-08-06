from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from betabox_robotics.launchpad.auth.session import Session


class SessionConstructionTests(unittest.TestCase):
    def test_constructs_session(
        self,
    ) -> None:
        session = Session(
            id="abc123",
            username="student1",
        )

        self.assertEqual(
            session.id,
            "abc123",
        )
        self.assertEqual(
            session.username,
            "student1",
        )

    def test_strips_fields(
        self,
    ) -> None:
        session = Session(
            id=" abc123 ",
            username=" student1 ",
        )

        self.assertEqual(
            session.id,
            "abc123",
        )
        self.assertEqual(
            session.username,
            "student1",
        )

    def test_allows_none_id(
        self,
    ) -> None:
        session = Session(
            id=None,
            username="guest",
        )

        self.assertIsNone(
            session.id,
        )

    def test_rejects_non_string_id(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "id must be a string or None",
        ):
            Session(
                id=123,  # type: ignore[arg-type]
                username="student",
            )

    def test_rejects_empty_id(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "id cannot be empty",
        ):
            Session(
                id=" ",
                username="student",
            )

    def test_rejects_non_string_username(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "username must be a string",
        ):
            Session(
                id="abc",
                username=1,  # type: ignore[arg-type]
            )

    def test_rejects_empty_username(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "username cannot be empty",
        ):
            Session(
                id="abc",
                username=" ",
            )

    def test_is_frozen(
        self,
    ) -> None:
        session = Session(
            id="abc",
            username="student",
        )

        with self.assertRaises(
            FrozenInstanceError,
        ):
            session.username = "other"  # type: ignore[misc]

    def test_is_slotted(
        self,
    ) -> None:
        session = Session(
            id="abc",
            username="student",
        )

        self.assertFalse(
            hasattr(
                session,
                "__dict__",
            )
        )


class GuestSessionTests(unittest.TestCase):
    def test_guest_factory(
        self,
    ) -> None:
        session = Session.guest()

        self.assertIsNone(
            session.id,
        )
        self.assertEqual(
            session.username,
            "guest",
        )
        self.assertTrue(
            session.guest_session,
        )

    def test_guest_property_false_for_normal_session(
        self,
    ) -> None:
        session = Session(
            id="abc",
            username="student",
        )

        self.assertFalse(
            session.guest_session,
        )

    def test_guest_property_false_when_guest_has_id(
        self,
    ) -> None:
        session = Session(
            id="abc",
            username="guest",
        )

        self.assertFalse(
            session.guest_session,
        )


class UsernameSessionTests(unittest.TestCase):
    def test_for_username(
        self,
    ) -> None:
        with patch("betabox_robotics.launchpad.auth.session.uuid4") as uuid4:
            uuid4.return_value.hex = "abcdef123456"

            session = Session.for_username("student1")

        self.assertEqual(
            session.id,
            "abcdef123456",
        )
        self.assertEqual(
            session.username,
            "student1",
        )

    def test_for_username_strips_username(
        self,
    ) -> None:
        with patch("betabox_robotics.launchpad.auth.session.uuid4") as uuid4:
            uuid4.return_value.hex = "abcdef"

            session = Session.for_username(" student1 ")

        self.assertEqual(
            session.username,
            "student1",
        )

    def test_for_username_rejects_guest(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "guest sessions must use Session.guest\\(\\)",
        ):
            Session.for_username("guest")

    def test_for_username_rejects_empty_username(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "username cannot be empty",
        ):
            Session.for_username(" ")


if __name__ == "__main__":
    unittest.main()
