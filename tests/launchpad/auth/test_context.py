from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.auth.context import LaunchpadContext
from betabox_robotics.launchpad.auth.identity import Identity, Role
from betabox_robotics.launchpad.auth.permissions import (
    Permission,
    Permissions,
)
from betabox_robotics.launchpad.auth.workspace import (
    Workspace,
    build_workspace,
)
from betabox_robotics.launchpad.services import LaunchpadServices


def make_platform() -> PlatformConfig:
    return object.__new__(PlatformConfig)


def make_services() -> LaunchpadServices:
    return object.__new__(LaunchpadServices)


def make_identity(
    role: Role = Role.GUEST,
    *,
    authenticated: bool | None = None,
) -> Identity:
    if authenticated is None:
        authenticated = role is not Role.GUEST

    return Identity(
        username=role.value,
        display_name=role.value.title(),
        role=role,
        authenticated=authenticated,
    )


def make_workspace(
    *,
    persistent: bool = False,
) -> Workspace:
    return build_workspace(
        Path("/home/test"),
        persistent=persistent,
    )


def make_permissions(
    *permissions: Permission,
) -> Permissions:
    return Permissions.from_iterable(permissions)


def make_context(
    *,
    identity: Identity | None = None,
    workspace: Workspace | None = None,
    permissions: Permissions | None = None,
) -> LaunchpadContext:
    return LaunchpadContext(
        platform=make_platform(),
        services=make_services(),
        identity=(make_identity() if identity is None else identity),
        workspace=(make_workspace() if workspace is None else workspace),
        permissions=(
            make_permissions(
                Permission.STATUS,
                Permission.EVENTS,
            )
            if permissions is None
            else permissions
        ),
    )


class LaunchpadContextConstructionTests(unittest.TestCase):
    def test_constructs_valid_context(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        identity = make_identity(Role.STUDENT)
        workspace = make_workspace(persistent=True)
        permissions = make_permissions(Permission.STATUS)

        context = LaunchpadContext(
            platform=platform,
            services=services,
            identity=identity,
            workspace=workspace,
            permissions=permissions,
        )

        self.assertIs(
            context.platform,
            platform,
        )
        self.assertIs(
            context.services,
            services,
        )
        self.assertIs(
            context.identity,
            identity,
        )
        self.assertIs(
            context.workspace,
            workspace,
        )
        self.assertIs(
            context.permissions,
            permissions,
        )

    def test_rejects_invalid_platform(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "platform must be a PlatformConfig",
        ):
            LaunchpadContext(
                platform=object(),  # type: ignore[arg-type]
                services=make_services(),
                identity=make_identity(),
                workspace=make_workspace(),
                permissions=make_permissions(),
            )

    def test_rejects_invalid_services(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "services must be LaunchpadServices",
        ):
            LaunchpadContext(
                platform=make_platform(),
                services=object(),  # type: ignore[arg-type]
                identity=make_identity(),
                workspace=make_workspace(),
                permissions=make_permissions(),
            )

    def test_rejects_invalid_identity(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "identity must be an Identity",
        ):
            LaunchpadContext(
                platform=make_platform(),
                services=make_services(),
                identity=object(),  # type: ignore[arg-type]
                workspace=make_workspace(),
                permissions=make_permissions(),
            )

    def test_rejects_invalid_workspace(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "workspace must be a Workspace",
        ):
            LaunchpadContext(
                platform=make_platform(),
                services=make_services(),
                identity=make_identity(),
                workspace=object(),  # type: ignore[arg-type]
                permissions=make_permissions(),
            )

    def test_rejects_invalid_permissions(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permissions must be Permissions",
        ):
            LaunchpadContext(
                platform=make_platform(),
                services=make_services(),
                identity=make_identity(),
                workspace=make_workspace(),
                permissions=object(),  # type: ignore[arg-type]
            )

    def test_is_frozen(
        self,
    ) -> None:
        context = make_context()

        with self.assertRaises(
            FrozenInstanceError,
        ):
            context.identity = make_identity(  # type: ignore[misc]
                Role.STUDENT
            )

    def test_is_slotted(
        self,
    ) -> None:
        context = make_context()

        self.assertFalse(
            hasattr(
                context,
                "__dict__",
            )
        )


class PermissionDelegationTests(unittest.TestCase):
    def test_can_returns_true_for_granted_permission(
        self,
    ) -> None:
        context = make_context(permissions=make_permissions(Permission.STATUS))

        self.assertTrue(context.can(Permission.STATUS))

    def test_can_returns_false_for_missing_permission(
        self,
    ) -> None:
        context = make_context(permissions=make_permissions(Permission.STATUS))

        self.assertFalse(context.can(Permission.ROBOT_DRIVE))

    def test_can_delegates_to_permissions(
        self,
    ) -> None:
        permissions = make_permissions()
        context = make_context(permissions=permissions)

        with patch.object(
            Permissions,
            "allows",
            return_value=True,
        ) as allows:
            result = context.can(Permission.STATUS)

        self.assertTrue(result)
        allows.assert_called_once_with(Permission.STATUS)

    def test_can_rejects_invalid_permission(
        self,
    ) -> None:
        context = make_context()

        with self.assertRaisesRegex(
            TypeError,
            "permission must be a Permission",
        ):
            context.can(
                "status"  # type: ignore[arg-type]
            )

    def test_require_returns_none_for_granted_permission(
        self,
    ) -> None:
        context = make_context(permissions=make_permissions(Permission.STATUS))

        self.assertIsNone(context.require(Permission.STATUS))

    def test_require_raises_for_missing_permission(
        self,
    ) -> None:
        context = make_context(permissions=make_permissions())

        with self.assertRaisesRegex(
            PermissionError,
            "Permission required: status",
        ):
            context.require(Permission.STATUS)

    def test_require_delegates_to_permissions(
        self,
    ) -> None:
        permissions = make_permissions()
        context = make_context(permissions=permissions)

        with patch.object(
            Permissions,
            "require",
        ) as require:
            context.require(Permission.EVENTS)

        require.assert_called_once_with(Permission.EVENTS)


class IdentityPropertyTests(unittest.TestCase):
    def test_guest_context_properties(
        self,
    ) -> None:
        context = make_context(
            identity=make_identity(
                Role.GUEST,
                authenticated=False,
            )
        )

        self.assertTrue(context.guest)
        self.assertFalse(context.student)
        self.assertFalse(context.teacher)
        self.assertFalse(context.authenticated)

    def test_student_context_properties(
        self,
    ) -> None:
        context = make_context(
            identity=make_identity(
                Role.STUDENT,
                authenticated=True,
            )
        )

        self.assertFalse(context.guest)
        self.assertTrue(context.student)
        self.assertFalse(context.teacher)
        self.assertTrue(context.authenticated)

    def test_teacher_context_properties(
        self,
    ) -> None:
        context = make_context(
            identity=make_identity(
                Role.TEACHER,
                authenticated=True,
            )
        )

        self.assertFalse(context.guest)
        self.assertFalse(context.student)
        self.assertTrue(context.teacher)
        self.assertTrue(context.authenticated)

    def test_properties_delegate_to_identity(
        self,
    ) -> None:
        identity = make_identity(Role.STUDENT)
        context = make_context(identity=identity)

        self.assertEqual(
            context.guest,
            identity.guest,
        )
        self.assertEqual(
            context.student,
            identity.student,
        )
        self.assertEqual(
            context.teacher,
            identity.teacher,
        )
        self.assertEqual(
            context.authenticated,
            identity.authenticated,
        )


class WorkspacePropertyTests(unittest.TestCase):
    def test_persistent_workspace_true(
        self,
    ) -> None:
        context = make_context(workspace=make_workspace(persistent=True))

        self.assertTrue(context.persistent_workspace)

    def test_persistent_workspace_false(
        self,
    ) -> None:
        context = make_context(workspace=make_workspace(persistent=False))

        self.assertFalse(context.persistent_workspace)

    def test_persistent_workspace_delegates_to_workspace(
        self,
    ) -> None:
        workspace = make_workspace(persistent=True)
        context = make_context(workspace=workspace)

        self.assertEqual(
            context.persistent_workspace,
            workspace.persistent,
        )


if __name__ == "__main__":
    unittest.main()
