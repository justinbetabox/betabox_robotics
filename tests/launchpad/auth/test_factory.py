from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.auth.context import LaunchpadContext
from betabox_robotics.launchpad.auth.factory import (
    _validate_platform,
    _validate_services,
    _validate_username,
    _validate_workspace_root,
    build_account_context,
    build_guest_context,
    role_for_username,
)
from betabox_robotics.launchpad.auth.identity import Role
from betabox_robotics.launchpad.auth.permissions import (
    ROLE_PERMISSIONS,
    Permissions,
)
from betabox_robotics.launchpad.auth.workspace import Workspace
from betabox_robotics.launchpad.services import LaunchpadServices


MODULE = "betabox_robotics.launchpad.auth.factory"


def make_platform() -> PlatformConfig:
    return object.__new__(
        PlatformConfig
    )


def make_services() -> LaunchpadServices:
    return object.__new__(
        LaunchpadServices
    )


def make_account(
    *,
    username: str = "student1",
    display_name: str = "Student 1",
    home: Path | None = None,
    persistent: bool = True,
) -> SimpleNamespace:
    if home is None:
        home = Path(
            f"/home/{username}"
        )

    return SimpleNamespace(
        username=username,
        display_name=display_name,
        home=home,
        persistent=persistent,
    )


def make_workspace(
    *,
    root: Path = Path("/home/student1"),
    persistent: bool = True,
) -> Mock:
    workspace = Mock(
        spec=Workspace
    )
    workspace.root = root
    workspace.persistent = persistent
    workspace.ensure_exists = Mock()
    return workspace


class ValidationTests(unittest.TestCase):
    def test_validate_username_strips(
        self,
    ) -> None:
        self.assertEqual(
            _validate_username(
                " student1 "
            ),
            "student1",
        )

    def test_validate_username_rejects_non_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "username must be a string",
        ):
            _validate_username(
                1
            )

    def test_validate_username_rejects_empty(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "username cannot be empty",
        ):
            _validate_username(
                " "
            )

    def test_validate_platform_accepts_platform_config(
        self,
    ) -> None:
        platform = make_platform()

        self.assertIs(
            _validate_platform(
                platform
            ),
            platform,
        )

    def test_validate_platform_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "platform must be a PlatformConfig",
        ):
            _validate_platform(
                object()
            )

    def test_validate_services_accepts_launchpad_services(
        self,
    ) -> None:
        services = make_services()

        self.assertIs(
            _validate_services(
                services
            ),
            services,
        )

    def test_validate_services_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "services must be LaunchpadServices",
        ):
            _validate_services(
                object()
            )

    def test_validate_workspace_root_accepts_none(
        self,
    ) -> None:
        self.assertIsNone(
            _validate_workspace_root(
                None
            )
        )

    def test_validate_workspace_root_accepts_path(
        self,
    ) -> None:
        root = Path(
            "/tmp/workspace"
        )

        self.assertIs(
            _validate_workspace_root(
                root
            ),
            root,
        )

    def test_validate_workspace_root_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "workspace_root must be a Path or None",
        ):
            _validate_workspace_root(
                "/tmp/workspace"
            )


class RoleForUsernameTests(unittest.TestCase):
    def test_guest_username_returns_guest_role(
        self,
    ) -> None:
        self.assertIs(
            role_for_username(
                "guest"
            ),
            Role.GUEST,
        )

    def test_guest_username_is_stripped(
        self,
    ) -> None:
        self.assertIs(
            role_for_username(
                " guest "
            ),
            Role.GUEST,
        )

    def test_other_username_returns_student_role(
        self,
    ) -> None:
        for username in (
            "student",
            "student1",
            "teacher",
            "admin",
        ):
            with self.subTest(
                username=username,
            ):
                self.assertIs(
                    role_for_username(
                        username
                    ),
                    Role.STUDENT,
                )

    def test_role_mapping_is_case_sensitive(
        self,
    ) -> None:
        self.assertIs(
            role_for_username(
                "Guest"
            ),
            Role.STUDENT,
        )

    def test_rejects_invalid_username(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "username cannot be empty",
        ):
            role_for_username(
                " "
            )


class BuildAccountContextTests(unittest.TestCase):
    def test_builds_student_context(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        account = make_account()
        workspace = make_workspace()
        permissions = Permissions.for_role(
            Role.STUDENT
        )
        context = Mock(
            spec=LaunchpadContext
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ) as lookup,
            patch(
                f"{MODULE}.build_workspace",
                return_value=workspace,
            ) as build_workspace,
            patch(
                f"{MODULE}.Permissions.for_role",
                return_value=permissions,
            ) as for_role,
            patch(
                f"{MODULE}.LaunchpadContext",
                return_value=context,
            ) as context_class,
        ):
            result = build_account_context(
                platform,
                services,
                " student1 ",
            )

        self.assertIs(
            result,
            context,
        )
        lookup.assert_called_once_with(
            "student1"
        )
        build_workspace.assert_called_once_with(
            account.home,
            persistent=True,
        )
        workspace.ensure_exists.assert_called_once_with()
        for_role.assert_called_once_with(
            Role.STUDENT
        )

        identity = (
            context_class.call_args.kwargs[
                "identity"
            ]
        )
        self.assertEqual(
            identity.username,
            "student1",
        )
        self.assertEqual(
            identity.display_name,
            "Student 1",
        )
        self.assertIs(
            identity.role,
            Role.STUDENT,
        )
        self.assertTrue(
            identity.authenticated,
        )

        context_class.assert_called_once_with(
            platform=platform,
            services=services,
            identity=identity,
            workspace=workspace,
            permissions=permissions,
        )

    def test_builds_guest_context_from_account(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        account = make_account(
            username="guest",
            display_name="Guest",
            home=Path("/home/guest"),
            persistent=False,
        )
        workspace = make_workspace(
            root=Path("/home/guest"),
            persistent=False,
        )
        context = Mock(
            spec=LaunchpadContext
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ),
            patch(
                f"{MODULE}.build_workspace",
                return_value=workspace,
            ),
            patch(
                f"{MODULE}.LaunchpadContext",
                return_value=context,
            ) as context_class,
        ):
            result = build_account_context(
                platform,
                services,
                "guest",
            )

        self.assertIs(
            result,
            context,
        )
        identity = (
            context_class.call_args.kwargs[
                "identity"
            ]
        )
        permissions = (
            context_class.call_args.kwargs[
                "permissions"
            ]
        )

        self.assertIs(
            identity.role,
            Role.GUEST,
        )
        self.assertFalse(
            identity.authenticated,
        )
        self.assertEqual(
            permissions.granted,
            ROLE_PERMISSIONS[
                Role.GUEST
            ],
        )

    def test_uses_workspace_override(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        account = make_account(
            persistent=True
        )
        override = Path(
            "/tmp/student-workspace"
        )
        workspace = make_workspace(
            root=override,
            persistent=True,
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ),
            patch(
                f"{MODULE}.build_workspace",
                return_value=workspace,
            ) as build_workspace,
            patch(
                f"{MODULE}.LaunchpadContext",
                return_value=Mock(
                    spec=LaunchpadContext
                ),
            ),
        ):
            build_account_context(
                platform,
                services,
                "student1",
                workspace_root=override,
            )

        build_workspace.assert_called_once_with(
            override,
            persistent=True,
        )

    def test_workspace_override_does_not_change_persistence(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        account = make_account(
            persistent=False
        )
        override = Path(
            "/tmp/guest-workspace"
        )
        workspace = make_workspace(
            root=override,
            persistent=False,
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ),
            patch(
                f"{MODULE}.build_workspace",
                return_value=workspace,
            ) as build_workspace,
            patch(
                f"{MODULE}.LaunchpadContext",
                return_value=Mock(
                    spec=LaunchpadContext
                ),
            ),
        ):
            build_account_context(
                platform,
                services,
                "guest",
                workspace_root=override,
            )

        build_workspace.assert_called_once_with(
            override,
            persistent=False,
        )

    def test_uses_canonical_account_username_for_role(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        account = make_account(
            username="guest",
            display_name="Guest",
            persistent=False,
        )
        workspace = make_workspace(
            persistent=False
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ),
            patch(
                f"{MODULE}.role_for_username",
                return_value=Role.GUEST,
            ) as role_for_username,
            patch(
                f"{MODULE}.build_workspace",
                return_value=workspace,
            ),
            patch(
                f"{MODULE}.LaunchpadContext",
                return_value=Mock(
                    spec=LaunchpadContext
                ),
            ),
        ):
            build_account_context(
                platform,
                services,
                "alias",
            )

        role_for_username.assert_called_once_with(
            "guest"
        )

    def test_account_lookup_error_propagates(
        self,
    ) -> None:
        error = LookupError(
            "missing"
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                side_effect=error,
            ),
            self.assertRaises(
                LookupError
            ) as context,
        ):
            build_account_context(
                make_platform(),
                make_services(),
                "missing",
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_workspace_creation_error_propagates(
        self,
    ) -> None:
        error = OSError(
            "permission denied"
        )
        workspace = make_workspace()
        workspace.ensure_exists.side_effect = error

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            patch(
                f"{MODULE}.build_workspace",
                return_value=workspace,
            ),
            self.assertRaises(
                OSError
            ) as context,
        ):
            build_account_context(
                make_platform(),
                make_services(),
                "student1",
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_platform_before_lookup(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username"
            ) as lookup,
            self.assertRaisesRegex(
                TypeError,
                "platform must be a PlatformConfig",
            ),
        ):
            build_account_context(
                object(),  # type: ignore[arg-type]
                make_services(),
                "student1",
            )

        lookup.assert_not_called()

    def test_rejects_invalid_services_before_lookup(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username"
            ) as lookup,
            self.assertRaisesRegex(
                TypeError,
                "services must be LaunchpadServices",
            ),
        ):
            build_account_context(
                make_platform(),
                object(),  # type: ignore[arg-type]
                "student1",
            )

        lookup.assert_not_called()

    def test_rejects_invalid_username_before_lookup(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username"
            ) as lookup,
            self.assertRaisesRegex(
                ValueError,
                "username cannot be empty",
            ),
        ):
            build_account_context(
                make_platform(),
                make_services(),
                " ",
            )

        lookup.assert_not_called()

    def test_rejects_invalid_workspace_root_before_lookup(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username"
            ) as lookup,
            self.assertRaisesRegex(
                TypeError,
                "workspace_root must be a Path or None",
            ),
        ):
            build_account_context(
                make_platform(),
                make_services(),
                "student1",
                workspace_root="/tmp",  # type: ignore[arg-type]
            )

        lookup.assert_not_called()


class BuildGuestContextTests(unittest.TestCase):
    def test_delegates_to_build_account_context(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        context = Mock(
            spec=LaunchpadContext
        )

        with patch(
            f"{MODULE}.build_account_context",
            return_value=context,
        ) as build_account:
            result = build_guest_context(
                platform,
                services,
            )

        self.assertIs(
            result,
            context,
        )
        build_account.assert_called_once_with(
            platform,
            services,
            "guest",
            workspace_root=None,
        )

    def test_forwards_workspace_override(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        root = Path(
            "/tmp/guest"
        )

        with patch(
            f"{MODULE}.build_account_context",
            return_value=Mock(
                spec=LaunchpadContext
            ),
        ) as build_account:
            build_guest_context(
                platform,
                services,
                workspace_root=root,
            )

        build_account.assert_called_once_with(
            platform,
            services,
            "guest",
            workspace_root=root,
        )

    def test_validation_is_delegated(
        self,
    ) -> None:
        error = TypeError(
            "platform must be a PlatformConfig"
        )

        with (
            patch(
                f"{MODULE}.build_account_context",
                side_effect=error,
            ),
            self.assertRaises(
                TypeError
            ) as context,
        ):
            build_guest_context(
                object(),  # type: ignore[arg-type]
                make_services(),
            )

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
