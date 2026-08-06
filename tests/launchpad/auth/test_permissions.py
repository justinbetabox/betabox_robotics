from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.launchpad.auth.identity import Role
from betabox_robotics.launchpad.auth.permissions import (
    GUEST_PERMISSIONS,
    ROLE_PERMISSIONS,
    STANDARD_PERMISSIONS,
    STUDENT_PERMISSIONS,
    TEACHER_PERMISSIONS,
    Permission,
    Permissions,
    _validate_permission,
    _validate_permissions,
)


class PermissionTests(unittest.TestCase):
    def test_values(
        self,
    ) -> None:
        expected = {
            Permission.ROBOT_DRIVE: "robot.drive",
            Permission.CODE: "code",
            Permission.VISION: "vision",
            Permission.MEDIA: "media",
            Permission.MEDIA_UPLOAD: "media.upload",
            Permission.MEDIA_DOWNLOAD: "media.download",
            Permission.CALIBRATION: "calibration",
            Permission.STATUS: "status",
            Permission.DIAGNOSTICS: "diagnostics",
            Permission.SERVICES: "services",
            Permission.INFORMATION: "information",
            Permission.PREFERENCES: "preferences",
            Permission.EVENTS: "events",
        }

        self.assertEqual(
            {
                permission: permission.value
                for permission in Permission
            },
            expected,
        )

    def test_members_are_strings(
        self,
    ) -> None:
        for permission in Permission:
            with self.subTest(
                permission=permission,
            ):
                self.assertIsInstance(
                    permission,
                    str,
                )
                self.assertEqual(
                    str(permission),
                    permission.value,
                )

    def test_constructs_from_value(
        self,
    ) -> None:
        self.assertIs(
            Permission("status"),
            Permission.STATUS,
        )
        self.assertIs(
            Permission("robot.drive"),
            Permission.ROBOT_DRIVE,
        )

    def test_rejects_unknown_value(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError,
        ):
            Permission("unknown")


class PermissionSetTests(unittest.TestCase):
    def test_standard_permissions_contains_every_permission(
        self,
    ) -> None:
        self.assertEqual(
            STANDARD_PERMISSIONS,
            frozenset(Permission),
        )

    def test_role_permission_sets_share_standard_permissions(
        self,
    ) -> None:
        self.assertIs(
            GUEST_PERMISSIONS,
            STANDARD_PERMISSIONS,
        )
        self.assertIs(
            STUDENT_PERMISSIONS,
            STANDARD_PERMISSIONS,
        )
        self.assertIs(
            TEACHER_PERMISSIONS,
            STANDARD_PERMISSIONS,
        )

    def test_role_mapping_is_complete(
        self,
    ) -> None:
        self.assertEqual(
            set(ROLE_PERMISSIONS),
            set(Role),
        )

    def test_role_mapping_uses_expected_sets(
        self,
    ) -> None:
        self.assertIs(
            ROLE_PERMISSIONS[Role.GUEST],
            GUEST_PERMISSIONS,
        )
        self.assertIs(
            ROLE_PERMISSIONS[Role.STUDENT],
            STUDENT_PERMISSIONS,
        )
        self.assertIs(
            ROLE_PERMISSIONS[Role.TEACHER],
            TEACHER_PERMISSIONS,
        )

    def test_permission_sets_are_immutable(
        self,
    ) -> None:
        self.assertIsInstance(
            STANDARD_PERMISSIONS,
            frozenset,
        )

        with self.assertRaises(
            AttributeError,
        ):
            STANDARD_PERMISSIONS.add(  # type: ignore[attr-defined]
                Permission.STATUS
            )


class ValidationTests(unittest.TestCase):
    def test_validate_permission_accepts_permission(
        self,
    ) -> None:
        self.assertIs(
            _validate_permission(
                Permission.STATUS
            ),
            Permission.STATUS,
        )

    def test_validate_permission_uses_custom_name(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "capability must be a Permission",
        ):
            _validate_permission(
                "status",
                name="capability",
            )

    def test_validate_permission_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            "status",
            1,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "permission must be a Permission",
                ),
            ):
                _validate_permission(
                    value
                )

    def test_validate_permissions_accepts_frozenset(
        self,
    ) -> None:
        granted = frozenset(
            {
                Permission.STATUS,
                Permission.EVENTS,
            }
        )

        self.assertIs(
            _validate_permissions(
                granted
            ),
            granted,
        )

    def test_validate_permissions_rejects_other_collections(
        self,
    ) -> None:
        for value in (
            set(),
            [],
            (),
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "granted must be a frozenset",
                ),
            ):
                _validate_permissions(
                    value
                )

    def test_validate_permissions_rejects_invalid_items(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "granted must contain only Permission values",
        ):
            _validate_permissions(
                frozenset(
                    {
                        Permission.STATUS,
                        "events",
                    }
                )
            )


class PermissionsConstructionTests(unittest.TestCase):
    def test_constructs_permissions(
        self,
    ) -> None:
        granted = frozenset(
            {
                Permission.STATUS,
                Permission.EVENTS,
            }
        )

        permissions = Permissions(
            granted=granted
        )

        self.assertIs(
            permissions.granted,
            granted,
        )

    def test_allows_empty_permission_set(
        self,
    ) -> None:
        permissions = Permissions(
            granted=frozenset()
        )

        self.assertEqual(
            permissions.granted,
            frozenset(),
        )

    def test_rejects_non_frozenset(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "granted must be a frozenset",
        ):
            Permissions(
                granted={  # type: ignore[arg-type]
                    Permission.STATUS
                }
            )

    def test_rejects_invalid_granted_item(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "granted must contain only Permission values",
        ):
            Permissions(
                granted=frozenset(
                    {
                        "status"
                    }
                )  # type: ignore[arg-type]
            )

    def test_is_frozen(
        self,
    ) -> None:
        permissions = Permissions(
            granted=frozenset(
                {
                    Permission.STATUS
                }
            )
        )

        with self.assertRaises(
            FrozenInstanceError,
        ):
            permissions.granted = frozenset()  # type: ignore[misc]

    def test_is_slotted(
        self,
    ) -> None:
        permissions = Permissions(
            granted=frozenset()
        )

        self.assertFalse(
            hasattr(
                permissions,
                "__dict__",
            )
        )


class ForRoleTests(unittest.TestCase):
    def test_builds_permissions_for_each_role(
        self,
    ) -> None:
        for role in Role:
            with self.subTest(
                role=role,
            ):
                permissions = (
                    Permissions.for_role(
                        role
                    )
                )

                self.assertIs(
                    permissions.granted,
                    ROLE_PERMISSIONS[role],
                )

    def test_all_roles_currently_have_standard_access(
        self,
    ) -> None:
        guest = Permissions.for_role(
            Role.GUEST
        )
        student = Permissions.for_role(
            Role.STUDENT
        )
        teacher = Permissions.for_role(
            Role.TEACHER
        )

        self.assertEqual(
            guest,
            student,
        )
        self.assertEqual(
            student,
            teacher,
        )
        self.assertEqual(
            guest.granted,
            STANDARD_PERMISSIONS,
        )

    def test_rejects_invalid_role(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "role must be a Role",
        ):
            Permissions.for_role(
                "guest"  # type: ignore[arg-type]
            )


class FromIterableTests(unittest.TestCase):
    def test_accepts_list(
        self,
    ) -> None:
        permissions = (
            Permissions.from_iterable(
                [
                    Permission.STATUS,
                    Permission.EVENTS,
                ]
            )
        )

        self.assertEqual(
            permissions.granted,
            frozenset(
                {
                    Permission.STATUS,
                    Permission.EVENTS,
                }
            ),
        )

    def test_accepts_tuple(
        self,
    ) -> None:
        permissions = (
            Permissions.from_iterable(
                (
                    Permission.STATUS,
                    Permission.EVENTS,
                )
            )
        )

        self.assertEqual(
            permissions.granted,
            frozenset(
                {
                    Permission.STATUS,
                    Permission.EVENTS,
                }
            ),
        )

    def test_accepts_set(
        self,
    ) -> None:
        permissions = (
            Permissions.from_iterable(
                {
                    Permission.STATUS,
                    Permission.EVENTS,
                }
            )
        )

        self.assertEqual(
            permissions.granted,
            frozenset(
                {
                    Permission.STATUS,
                    Permission.EVENTS,
                }
            ),
        )

    def test_accepts_frozenset(
        self,
    ) -> None:
        granted = frozenset(
            {
                Permission.STATUS,
                Permission.EVENTS,
            }
        )

        permissions = (
            Permissions.from_iterable(
                granted
            )
        )

        self.assertEqual(
            permissions.granted,
            granted,
        )

    def test_accepts_generator(
        self,
    ) -> None:
        permissions = (
            Permissions.from_iterable(
                permission
                for permission in (
                    Permission.STATUS,
                    Permission.EVENTS,
                )
            )
        )

        self.assertEqual(
            permissions.granted,
            frozenset(
                {
                    Permission.STATUS,
                    Permission.EVENTS,
                }
            ),
        )

    def test_removes_duplicates(
        self,
    ) -> None:
        permissions = (
            Permissions.from_iterable(
                [
                    Permission.STATUS,
                    Permission.STATUS,
                ]
            )
        )

        self.assertEqual(
            permissions.granted,
            frozenset(
                {
                    Permission.STATUS
                }
            ),
        )

    def test_accepts_empty_iterable(
        self,
    ) -> None:
        permissions = (
            Permissions.from_iterable(
                []
            )
        )

        self.assertEqual(
            permissions.granted,
            frozenset(),
        )

    def test_rejects_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permissions must be an iterable",
        ):
            Permissions.from_iterable(
                "status"  # type: ignore[arg-type]
            )

    def test_rejects_bytes(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permissions must be an iterable",
        ):
            Permissions.from_iterable(
                b"status"  # type: ignore[arg-type]
            )

    def test_rejects_non_iterable(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permissions must be an iterable",
        ):
            Permissions.from_iterable(
                1  # type: ignore[arg-type]
            )

    def test_rejects_invalid_items(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permissions must contain only Permission values",
        ):
            Permissions.from_iterable(
                [
                    Permission.STATUS,
                    "events",
                ]  # type: ignore[list-item]
            )


class AllowsTests(unittest.TestCase):
    def setUp(
        self,
    ) -> None:
        self.permissions = (
            Permissions.from_iterable(
                [
                    Permission.STATUS,
                    Permission.EVENTS,
                ]
            )
        )

    def test_returns_true_for_granted_permission(
        self,
    ) -> None:
        self.assertTrue(
            self.permissions.allows(
                Permission.STATUS
            )
        )

    def test_returns_false_for_missing_permission(
        self,
    ) -> None:
        self.assertFalse(
            self.permissions.allows(
                Permission.ROBOT_DRIVE
            )
        )

    def test_rejects_invalid_permission(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permission must be a Permission",
        ):
            self.permissions.allows(
                "status"  # type: ignore[arg-type]
            )


class RequireTests(unittest.TestCase):
    def setUp(
        self,
    ) -> None:
        self.permissions = (
            Permissions.from_iterable(
                [
                    Permission.STATUS,
                    Permission.EVENTS,
                ]
            )
        )

    def test_returns_none_for_granted_permission(
        self,
    ) -> None:
        self.assertIsNone(
            self.permissions.require(
                Permission.STATUS
            )
        )

    def test_raises_for_missing_permission(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            PermissionError,
            "Permission required: robot\\.drive",
        ):
            self.permissions.require(
                Permission.ROBOT_DRIVE
            )

    def test_rejects_invalid_permission(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permission must be a Permission",
        ):
            self.permissions.require(
                "status"  # type: ignore[arg-type]
            )


class ContainsTests(unittest.TestCase):
    def setUp(
        self,
    ) -> None:
        self.permissions = (
            Permissions.from_iterable(
                [
                    Permission.STATUS,
                    Permission.EVENTS,
                ]
            )
        )

    def test_contains_granted_permission(
        self,
    ) -> None:
        self.assertIn(
            Permission.STATUS,
            self.permissions,
        )

    def test_does_not_contain_missing_permission(
        self,
    ) -> None:
        self.assertNotIn(
            Permission.ROBOT_DRIVE,
            self.permissions,
        )

    def test_unrelated_object_returns_false(
        self,
    ) -> None:
        self.assertNotIn(
            "status",
            self.permissions,
        )
        self.assertNotIn(
            object(),
            self.permissions,
        )


if __name__ == "__main__":
    unittest.main()
