from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.launchpad.auth.identity import (
    Identity,
    Role,
)


class RoleTests(unittest.TestCase):
    def test_values(
        self,
    ) -> None:
        self.assertEqual(
            Role.GUEST.value,
            "guest",
        )
        self.assertEqual(
            Role.STUDENT.value,
            "student",
        )
        self.assertEqual(
            Role.TEACHER.value,
            "teacher",
        )

    def test_members_are_strings(
        self,
    ) -> None:
        for role in Role:
            with self.subTest(
                role=role,
            ):
                self.assertIsInstance(
                    role,
                    str,
                )
                self.assertEqual(
                    str(role),
                    role.value,
                )

    def test_constructs_from_value(
        self,
    ) -> None:
        self.assertIs(
            Role("guest"),
            Role.GUEST,
        )
        self.assertIs(
            Role("student"),
            Role.STUDENT,
        )
        self.assertIs(
            Role("teacher"),
            Role.TEACHER,
        )

    def test_rejects_unknown_value(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError,
        ):
            Role("admin")


class IdentityConstructionTests(unittest.TestCase):
    def test_constructs_guest_identity(
        self,
    ) -> None:
        identity = Identity(
            username="guest",
            display_name="Guest",
            role=Role.GUEST,
            authenticated=False,
        )

        self.assertEqual(
            identity.username,
            "guest",
        )
        self.assertEqual(
            identity.display_name,
            "Guest",
        )
        self.assertIs(
            identity.role,
            Role.GUEST,
        )
        self.assertFalse(
            identity.authenticated,
        )

    def test_strips_username_and_display_name(
        self,
    ) -> None:
        identity = Identity(
            username=" student1 ",
            display_name=" Student 1 ",
            role=Role.STUDENT,
            authenticated=True,
        )

        self.assertEqual(
            identity.username,
            "student1",
        )
        self.assertEqual(
            identity.display_name,
            "Student 1",
        )

    def test_rejects_non_string_username(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "username must be a string",
        ):
            Identity(
                username=1,  # type: ignore[arg-type]
                display_name="Student",
                role=Role.STUDENT,
                authenticated=True,
            )

    def test_rejects_empty_username(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "username cannot be empty",
        ):
            Identity(
                username=" ",
                display_name="Student",
                role=Role.STUDENT,
                authenticated=True,
            )

    def test_rejects_non_string_display_name(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "display_name must be a string",
        ):
            Identity(
                username="student",
                display_name=1,  # type: ignore[arg-type]
                role=Role.STUDENT,
                authenticated=True,
            )

    def test_rejects_empty_display_name(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "display_name cannot be empty",
        ):
            Identity(
                username="student",
                display_name=" ",
                role=Role.STUDENT,
                authenticated=True,
            )

    def test_rejects_invalid_role(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "role must be a Role",
        ):
            Identity(
                username="guest",
                display_name="Guest",
                role="guest",  # type: ignore[arg-type]
                authenticated=False,
            )

    def test_rejects_invalid_authenticated_flag(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "authenticated must be a boolean",
        ):
            Identity(
                username="student",
                display_name="Student",
                role=Role.STUDENT,
                authenticated=1,  # type: ignore[arg-type]
            )

    def test_is_frozen(
        self,
    ) -> None:
        identity = Identity(
            username="student",
            display_name="Student",
            role=Role.STUDENT,
            authenticated=True,
        )

        with self.assertRaises(
            FrozenInstanceError,
        ):
            identity.username = "changed"  # type: ignore[misc]

    def test_is_slotted(
        self,
    ) -> None:
        identity = Identity(
            username="student",
            display_name="Student",
            role=Role.STUDENT,
            authenticated=True,
        )

        self.assertFalse(
            hasattr(
                identity,
                "__dict__",
            )
        )


class IdentityRolePropertyTests(unittest.TestCase):
    def test_guest_properties(
        self,
    ) -> None:
        identity = Identity(
            username="guest",
            display_name="Guest",
            role=Role.GUEST,
            authenticated=False,
        )

        self.assertTrue(
            identity.guest,
        )
        self.assertFalse(
            identity.student,
        )
        self.assertFalse(
            identity.teacher,
        )

    def test_student_properties(
        self,
    ) -> None:
        identity = Identity(
            username="student",
            display_name="Student",
            role=Role.STUDENT,
            authenticated=True,
        )

        self.assertFalse(
            identity.guest,
        )
        self.assertTrue(
            identity.student,
        )
        self.assertFalse(
            identity.teacher,
        )

    def test_teacher_properties(
        self,
    ) -> None:
        identity = Identity(
            username="teacher",
            display_name="Teacher",
            role=Role.TEACHER,
            authenticated=True,
        )

        self.assertFalse(
            identity.guest,
        )
        self.assertFalse(
            identity.student,
        )
        self.assertTrue(
            identity.teacher,
        )

    def test_authenticated_is_independent_of_role_properties(
        self,
    ) -> None:
        identity = Identity(
            username="student",
            display_name="Student",
            role=Role.STUDENT,
            authenticated=False,
        )

        self.assertTrue(
            identity.student,
        )
        self.assertFalse(
            identity.authenticated,
        )


if __name__ == "__main__":
    unittest.main()
