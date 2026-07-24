from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import jinja2
from aiohttp import web
from aiohttp.test_utils import (
    TestClient,
    TestServer,
)
from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.auth import (
    LAUNCHPAD_CONTEXT_KEY,
    LAUNCHPAD_CONTEXT_PROVIDER_KEY,
    LaunchpadContext,
    LaunchpadContextProvider,
    Permission,
    Permissions,
    Role,
    build_account_context,
    build_guest_context,
    build_permission_checker,
    build_workspace,
    launchpad_context_middleware,
    launchpad_template_context,
)
from betabox_robotics.launchpad.services import (
    LAUNCHPAD_SERVICES_KEY,
    LaunchpadServices,
)


def create_test_services() -> LaunchpadServices:
    return LaunchpadServices(
        calibration_manager=Mock(),
        calibration_service=Mock(),
        status_cache=Mock(),
    )


class WorkspaceTests(unittest.TestCase):
    def test_build_workspace_uses_expected_layout(
        self,
    ) -> None:
        root = Path("/tmp/example-workspace")

        workspace = build_workspace(
            root,
            persistent=True,
        )

        self.assertEqual(
            workspace.root,
            root,
        )
        self.assertEqual(
            workspace.curriculum,
            root / "curriculum",
        )
        self.assertEqual(
            workspace.media.pictures,
            root / "media" / "pictures",
        )
        self.assertEqual(
            workspace.media.videos,
            root / "media" / "videos",
        )
        self.assertEqual(
            workspace.media.sounds,
            root / "media" / "sounds",
        )
        self.assertEqual(
            workspace.preferences,
            root / "preferences",
        )
        self.assertTrue(workspace.persistent)

    def test_workspace_can_create_directories(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"

            workspace = build_workspace(
                root,
                persistent=False,
            )

            workspace.ensure_exists()

            for directory in workspace.directories():
                self.assertTrue(directory.is_dir())


class GuestContextTests(unittest.TestCase):
    def test_guest_context_has_guest_identity(
        self,
    ) -> None:
        platform = PlatformConfig.default()

        with tempfile.TemporaryDirectory() as temporary:
            context = build_guest_context(
                platform,
                create_test_services(),
                workspace_root=Path(temporary),
            )

            self.assertEqual(
                context.identity.username,
                "guest",
            )
            self.assertEqual(
                context.identity.display_name,
                "Guest",
            )
            self.assertIs(
                context.identity.role,
                Role.GUEST,
            )
            self.assertFalse(context.identity.authenticated)

    def test_guest_workspace_is_temporary(
        self,
    ) -> None:
        platform = PlatformConfig.default()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            context = build_guest_context(
                platform,
                create_test_services(),
                workspace_root=root,
            )

            self.assertEqual(
                context.workspace.root,
                root.resolve(),
            )
            self.assertFalse(context.workspace.persistent)
            self.assertIn(
                Permission.STATUS,
                context.permissions,
            )
            self.assertIn(
                Permission.VISION,
                context.permissions,
            )
            self.assertIn(
                Permission.ROBOT_DRIVE,
                context.permissions,
            )

            for directory in context.workspace.directories():
                self.assertTrue(directory.is_dir())

    def test_guest_context_role_properties(
        self,
    ) -> None:
        platform = PlatformConfig.default()

        with tempfile.TemporaryDirectory() as temporary:
            context = build_guest_context(
                platform,
                create_test_services(),
                workspace_root=Path(temporary),
            )

            self.assertTrue(context.guest)
            self.assertFalse(context.student)
            self.assertFalse(context.teacher)
            self.assertFalse(context.authenticated)
            self.assertFalse(context.persistent_workspace)

    def test_guest_context_can_check_permissions(
        self,
    ) -> None:
        platform = PlatformConfig.default()

        with tempfile.TemporaryDirectory() as temporary:
            context = build_guest_context(
                platform,
                create_test_services(),
                workspace_root=Path(temporary),
            )

            self.assertTrue(context.can(Permission.STATUS))
            self.assertTrue(context.can(Permission.ROBOT_DRIVE))

    def test_guest_context_can_require_permission(
        self,
    ) -> None:
        platform = PlatformConfig.default()

        with tempfile.TemporaryDirectory() as temporary:
            context = build_guest_context(
                platform,
                create_test_services(),
                workspace_root=Path(temporary),
            )

            context.require(Permission.STATUS)


class ContextMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_middleware_attaches_guest_context(
        self,
    ) -> None:
        platform = PlatformConfig.default()

        app = web.Application(
            middlewares=[
                launchpad_context_middleware,
            ]
        )

        app[LAUNCHPAD_CONTEXT_PROVIDER_KEY] = LaunchpadContextProvider(platform)

        app[LAUNCHPAD_SERVICES_KEY] = create_test_services()

        async def handler(
            request: web.Request,
        ) -> web.Response:
            context = request[LAUNCHPAD_CONTEXT_KEY]

            self.assertIsInstance(
                context,
                LaunchpadContext,
            )

            return web.json_response({"role": (context.identity.role.value)})

        app.router.add_get("/", handler)

        async with TestServer(app) as server, TestClient(server) as client:
            response = await client.get("/")
            payload = await response.json()

        self.assertEqual(
            payload["role"],
            Role.GUEST.value,
        )


class PermissionTests(unittest.TestCase):
    def test_guest_has_standard_permissions(
        self,
    ) -> None:
        permissions = Permissions.for_role(Role.GUEST)

        self.assertIn(Permission.ROBOT_DRIVE, permissions)
        self.assertIn(Permission.CODE, permissions)
        self.assertIn(Permission.VISION, permissions)
        self.assertIn(Permission.MEDIA, permissions)
        self.assertIn(Permission.MEDIA_UPLOAD, permissions)
        self.assertIn(Permission.MEDIA_DOWNLOAD, permissions)
        self.assertIn(Permission.CALIBRATION, permissions)
        self.assertIn(Permission.STATUS, permissions)
        self.assertIn(Permission.DIAGNOSTICS, permissions)
        self.assertIn(Permission.SERVICES, permissions)
        self.assertIn(Permission.INFORMATION, permissions)
        self.assertIn(Permission.PREFERENCES, permissions)
        self.assertIn(Permission.EVENTS, permissions)

    def test_student_permissions_match_guest(self):
        guest = Permissions.for_role(Role.GUEST)
        student = Permissions.for_role(Role.STUDENT)

        self.assertEqual(
            guest.granted,
            student.granted,
        )

    def test_teacher_permissions_match_student(self):
        teacher = Permissions.for_role(Role.TEACHER)
        student = Permissions.for_role(Role.STUDENT)

        self.assertEqual(
            teacher.granted,
            student.granted,
        )

    def test_requires_accepts_granted_permission(
        self,
    ) -> None:
        permissions = Permissions.for_role(Role.GUEST)

        permissions.require(Permission.STATUS)

    def test_unknown_explicit_permissions_can_be_built(
        self,
    ) -> None:
        permissions = Permissions.from_iterable(
            {
                Permission.STATUS,
                Permission.ROBOT_DRIVE,
            }
        )

        self.assertEqual(
            permissions.granted,
            frozenset(
                {
                    Permission.STATUS,
                    Permission.ROBOT_DRIVE,
                }
            ),
        )


class TemplateContextTests(unittest.IsolatedAsyncioTestCase):
    def build_context(
        self,
        root: Path,
    ) -> LaunchpadContext:
        return build_guest_context(
            PlatformConfig.default(),
            create_test_services(),
            workspace_root=root,
        )

    async def test_template_context_exposes_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.build_context(Path(temporary))

            request = {
                LAUNCHPAD_CONTEXT_KEY: context,
            }

            template_context = await launchpad_template_context(
                request  # type: ignore[arg-type]
            )

            self.assertIs(
                template_context["launchpad"],
                context,
            )
            self.assertIs(
                template_context["identity"],
                context.identity,
            )
            self.assertTrue(template_context["is_guest"])
            self.assertFalse(template_context["is_student"])
            self.assertFalse(template_context["is_teacher"])
            self.assertFalse(template_context["is_authenticated"])

    async def test_template_can_checks_permission(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.build_context(Path(temporary))

            request = {
                LAUNCHPAD_CONTEXT_KEY: context,
            }

            template_context = await launchpad_template_context(
                request  # type: ignore[arg-type]
            )

            can = template_context["can"]

            self.assertTrue(can("status"))
            self.assertTrue(can("vision"))
            self.assertTrue(can("robot.drive"))

    def test_permission_checker_rejects_unknown_value(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.build_context(Path(temporary))

            can = build_permission_checker(context)

            with self.assertRaisesRegex(
                ValueError,
                "Unknown Launchpad permission",
            ):
                can("robot.drve")


class IdentityBadgeTemplateTests(unittest.TestCase):
    def test_guest_identity_badge_renders(
        self,
    ) -> None:
        template_root = Path(__file__).parents[2] / "launchpad" / "templates"

        environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_root),
            autoescape=True,
        )

        template = environment.get_template("_identity_badge.html")

        rendered = template.render(
            identity=type(
                "Identity",
                (),
                {
                    "display_name": "Guest",
                    "role": Role.GUEST,
                },
            )(),
            is_guest=True,
            is_student=False,
            is_teacher=False,
        )

        self.assertIn(
            "Guest",
            rendered,
        )
        self.assertIn(
            "Guest session",
            rendered,
        )
        self.assertIn(
            'aria-label="Current Launchpad user"',
            rendered,
        )


class AccountContextTests(unittest.TestCase):
    def test_student_context_is_persistent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = build_account_context(
                PlatformConfig.default(),
                create_test_services(),
                "student1",
                workspace_root=Path(temporary),
            )

            self.assertEqual(
                context.identity.username,
                "student1",
            )
            self.assertEqual(
                context.identity.display_name,
                "Student 1",
            )
            self.assertIs(
                context.identity.role,
                Role.STUDENT,
            )
            self.assertTrue(context.identity.authenticated)
            self.assertTrue(context.workspace.persistent)

    def test_guest_and_student_permissions_match(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as guest_directory,
            tempfile.TemporaryDirectory() as student_directory,
        ):
            guest = build_account_context(
                PlatformConfig.default(),
                create_test_services(),
                "guest",
                workspace_root=Path(guest_directory),
            )

            student = build_account_context(
                PlatformConfig.default(),
                create_test_services(),
                "student1",
                workspace_root=Path(student_directory),
            )

            self.assertEqual(
                guest.permissions.granted,
                student.permissions.granted,
            )

    def test_unknown_account_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(LookupError):
            build_account_context(
                PlatformConfig.default(),
                create_test_services(),
                "unknown",
            )


if __name__ == "__main__":
    unittest.main()
