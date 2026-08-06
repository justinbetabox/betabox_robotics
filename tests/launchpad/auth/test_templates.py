from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.auth.context import LaunchpadContext
from betabox_robotics.launchpad.auth.identity import Identity, Role
from betabox_robotics.launchpad.auth.permissions import (
    Permission,
    Permissions,
)
from betabox_robotics.launchpad.auth.provider import (
    LAUNCHPAD_CONTEXT_KEY,
)
from betabox_robotics.launchpad.auth.templates import (
    _validate_context,
    _validate_permission_value,
    _validate_request,
    build_permission_checker,
    launchpad_template_context,
)
from betabox_robotics.launchpad.auth.workspace import (
    build_workspace,
)
from betabox_robotics.launchpad.services import LaunchpadServices


MODULE = "betabox_robotics.launchpad.auth.templates"


def make_platform() -> PlatformConfig:
    return object.__new__(
        PlatformConfig
    )


def make_services() -> LaunchpadServices:
    return object.__new__(
        LaunchpadServices
    )


def make_context(
    *,
    role: Role = Role.GUEST,
    authenticated: bool | None = None,
    permissions: Permissions | None = None,
) -> LaunchpadContext:
    if authenticated is None:
        authenticated = (
            role is not Role.GUEST
        )

    if permissions is None:
        permissions = (
            Permissions.from_iterable(
                [
                    Permission.STATUS,
                    Permission.EVENTS,
                ]
            )
        )

    return LaunchpadContext(
        platform=make_platform(),
        services=make_services(),
        identity=Identity(
            username=role.value,
            display_name=role.value.title(),
            role=role,
            authenticated=authenticated,
        ),
        workspace=build_workspace(
            Path(
                f"/home/{role.value}"
            ),
            persistent=(
                role is not Role.GUEST
            ),
        ),
        permissions=permissions,
    )


def make_request(
    *,
    context: LaunchpadContext,
    query: dict[str, str] | None = None,
) -> Mock:
    request = Mock(
        spec=web.Request
    )
    request.query = (
        {}
        if query is None
        else query
    )
    request.__getitem__ = Mock(
        side_effect=lambda key: (
            context
            if key is LAUNCHPAD_CONTEXT_KEY
            else (_ for _ in ()).throw(
                KeyError(key)
            )
        )
    )
    return request


class ValidationTests(unittest.TestCase):
    def test_validate_context_accepts_context(
        self,
    ) -> None:
        context = make_context()

        self.assertIs(
            _validate_context(
                context
            ),
            context,
        )

    def test_validate_context_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "context must be a LaunchpadContext",
        ):
            _validate_context(
                object()
            )

    def test_validate_permission_value_strips(
        self,
    ) -> None:
        self.assertEqual(
            _validate_permission_value(
                " status "
            ),
            "status",
        )

    def test_validate_permission_value_rejects_non_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "permission_value must be a string",
        ):
            _validate_permission_value(
                1
            )

    def test_validate_permission_value_rejects_empty(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "permission_value cannot be empty",
        ):
            _validate_permission_value(
                " "
            )

    def test_validate_request_accepts_request(
        self,
    ) -> None:
        request = object.__new__(
            web.Request
        )

        self.assertIs(
            _validate_request(
                request
            ),
            request,
        )

    def test_validate_request_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "request must be a web.Request",
        ):
            _validate_request(
                object()
            )


class PermissionCheckerTests(unittest.TestCase):
    def test_returns_true_for_granted_permission(
        self,
    ) -> None:
        context = make_context(
            permissions=Permissions.from_iterable(
                [
                    Permission.STATUS
                ]
            )
        )
        can = build_permission_checker(
            context
        )

        self.assertTrue(
            can(
                "status"
            )
        )

    def test_returns_false_for_missing_permission(
        self,
    ) -> None:
        context = make_context(
            permissions=Permissions.from_iterable(
                [
                    Permission.STATUS
                ]
            )
        )
        can = build_permission_checker(
            context
        )

        self.assertFalse(
            can(
                "robot.drive"
            )
        )

    def test_strips_permission_value(
        self,
    ) -> None:
        context = make_context(
            permissions=Permissions.from_iterable(
                [
                    Permission.STATUS
                ]
            )
        )
        can = build_permission_checker(
            context
        )

        self.assertTrue(
            can(
                " status "
            )
        )

    def test_delegates_to_context_can(
        self,
    ) -> None:
        context = make_context()

        with patch.object(
            LaunchpadContext,
            "can",
            return_value=True,
        ) as context_can:
            can = build_permission_checker(
                context
            )
            result = can(
                "events"
            )

        self.assertTrue(
            result
        )
        context_can.assert_called_once_with(
            Permission.EVENTS
        )

    def test_rejects_unknown_permission(
        self,
    ) -> None:
        can = build_permission_checker(
            make_context()
        )

        with self.assertRaisesRegex(
            ValueError,
            "Unknown Launchpad permission: 'unknown'",
        ) as context:
            can(
                "unknown"
            )

        self.assertIsInstance(
            context.exception.__cause__,
            ValueError,
        )

    def test_rejects_empty_permission_value(
        self,
    ) -> None:
        can = build_permission_checker(
            make_context()
        )

        with self.assertRaisesRegex(
            ValueError,
            "permission_value cannot be empty",
        ):
            can(
                " "
            )

    def test_rejects_non_string_permission_value(
        self,
    ) -> None:
        can = build_permission_checker(
            make_context()
        )

        with self.assertRaisesRegex(
            TypeError,
            "permission_value must be a string",
        ):
            can(
                1  # type: ignore[arg-type]
            )

    def test_rejects_invalid_context(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "context must be a LaunchpadContext",
        ):
            build_permission_checker(
                object()  # type: ignore[arg-type]
            )


class TemplateContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_builds_guest_template_context(
        self,
    ) -> None:
        context = make_context(
            role=Role.GUEST,
            authenticated=False,
        )
        request = make_request(
            context=context,
        )

        with patch(
            f"{MODULE}._validate_request",
            return_value=request,
        ):
            result = await launchpad_template_context(
                request
            )

        self.assertIs(
            result["launchpad"],
            context,
        )
        self.assertIs(
            result["identity"],
            context.identity,
        )
        self.assertTrue(
            result["is_guest"]
        )
        self.assertFalse(
            result["is_student"]
        )
        self.assertFalse(
            result["is_teacher"]
        )
        self.assertFalse(
            result["is_authenticated"]
        )
        self.assertFalse(
            result["login_failed"]
        )
        self.assertTrue(
            callable(
                result["can"]
            )
        )
        self.assertTrue(
            result["can"](
                "status"
            )
        )

    async def test_builds_student_template_context(
        self,
    ) -> None:
        context = make_context(
            role=Role.STUDENT,
            authenticated=True,
        )
        request = make_request(
            context=context,
        )

        with patch(
            f"{MODULE}._validate_request",
            return_value=request,
        ):
            result = await launchpad_template_context(
                request
            )

        self.assertFalse(
            result["is_guest"]
        )
        self.assertTrue(
            result["is_student"]
        )
        self.assertFalse(
            result["is_teacher"]
        )
        self.assertTrue(
            result["is_authenticated"]
        )

    async def test_builds_teacher_template_context(
        self,
    ) -> None:
        context = make_context(
            role=Role.TEACHER,
            authenticated=True,
        )
        request = make_request(
            context=context,
        )

        with patch(
            f"{MODULE}._validate_request",
            return_value=request,
        ):
            result = await launchpad_template_context(
                request
            )

        self.assertFalse(
            result["is_guest"]
        )
        self.assertFalse(
            result["is_student"]
        )
        self.assertTrue(
            result["is_teacher"]
        )
        self.assertTrue(
            result["is_authenticated"]
        )

    async def test_login_failed_true_for_failed_query(
        self,
    ) -> None:
        context = make_context()
        request = make_request(
            context=context,
            query={
                "login": "failed",
            },
        )

        with patch(
            f"{MODULE}._validate_request",
            return_value=request,
        ):
            result = await launchpad_template_context(
                request
            )

        self.assertTrue(
            result["login_failed"]
        )

    async def test_login_failed_false_for_other_values(
        self,
    ) -> None:
        context = make_context()

        for query in (
            {},
            {
                "login": "",
            },
            {
                "login": "true",
            },
            {
                "login": "FAILED",
            },
        ):
            with self.subTest(
                query=query,
            ):
                request = make_request(
                    context=context,
                    query=query,
                )

                with patch(
                    f"{MODULE}._validate_request",
                    return_value=request,
                ):
                    result = await launchpad_template_context(
                        request
                    )

                self.assertFalse(
                    result["login_failed"]
                )

    async def test_reads_context_from_typed_request_key(
        self,
    ) -> None:
        context = make_context()
        request = make_request(
            context=context,
        )

        with patch(
            f"{MODULE}._validate_request",
            return_value=request,
        ):
            await launchpad_template_context(
                request
            )

        request.__getitem__.assert_called_once_with(
            LAUNCHPAD_CONTEXT_KEY
        )

    async def test_rejects_invalid_context_wiring(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.query = {}
        request.__getitem__ = Mock(
            return_value=object()
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            self.assertRaisesRegex(
                TypeError,
                "Launchpad context is invalid",
            ),
        ):
            await launchpad_template_context(
                request
            )

    async def test_missing_context_key_error_propagates(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.query = {}
        request.__getitem__ = Mock(
            side_effect=KeyError(
                LAUNCHPAD_CONTEXT_KEY
            )
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            self.assertRaises(
                KeyError
            ),
        ):
            await launchpad_template_context(
                request
            )

    async def test_invalid_request_is_rejected_before_access(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "request must be a web.Request",
        ):
            await launchpad_template_context(
                object()  # type: ignore[arg-type]
            )

    async def test_permission_checker_is_bound_to_context(
        self,
    ) -> None:
        context = make_context(
            permissions=Permissions.from_iterable(
                [
                    Permission.EVENTS
                ]
            )
        )
        request = make_request(
            context=context,
        )

        with patch(
            f"{MODULE}._validate_request",
            return_value=request,
        ):
            result = await launchpad_template_context(
                request
            )

        can = result["can"]

        self.assertTrue(
            can(
                "events"
            )
        )
        self.assertFalse(
            can(
                "status"
            )
        )


if __name__ == "__main__":
    unittest.main()
