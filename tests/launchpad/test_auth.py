from __future__ import annotations

from aiohttp import web
from aiohttp.test_utils import (
    TestClient,
    TestServer,
)

import tempfile
import unittest
from pathlib import Path

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.auth import (
    LaunchpadContext,
    LaunchpadContextProvider,
    Permission,
    Permissions,
    Role,
    build_guest_context,
    build_workspace,
    launchpad_context_middleware,
)

from unittest.mock import Mock

from betabox_robotics.launchpad.services import (
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
            self.assertFalse(
                context.identity.authenticated
            )

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
            self.assertFalse(
                context.workspace.persistent
            )
            self.assertFalse(
                context.permissions.administration
            )
            self.assertIn(
                Permission.ROBOT_STATUS,
                context.permissions,
            )
            self.assertIn(
                Permission.VISION_VIEW,
                context.permissions,
            )
            self.assertNotIn(
                Permission.ROBOT_DRIVE,
                context.permissions,
            )

            for directory in context.workspace.directories():
                self.assertTrue(directory.is_dir())


class ContextMiddlewareTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_middleware_attaches_guest_context(
        self,
    ) -> None:
        platform = PlatformConfig.default()

        app = web.Application(
            middlewares=[
                launchpad_context_middleware,
            ]
        )

        app["context_provider"] = (
            LaunchpadContextProvider(platform)
        )

        app["launchpad_services"] = (
            create_test_services()
        )

        async def handler(
            request: web.Request,
        ) -> web.Response:
            context = request[
                "launchpad_context"
            ]

            self.assertIsInstance(
                context,
                LaunchpadContext,
            )

            return web.json_response(
                {
                    "role": (
                        context.identity.role.value
                    )
                }
            )

        app.router.add_get("/", handler)

        async with TestServer(app) as server:
            async with TestClient(server) as client:
                response = await client.get("/")
                payload = await response.json()

        self.assertEqual(
            payload["role"],
            Role.GUEST.value,
        )

class PermissionTests(unittest.TestCase):
    def test_guest_has_read_only_permissions(
        self,
    ) -> None:
        permissions = Permissions.for_role(
            Role.GUEST
        )

        self.assertIn(
            Permission.ROBOT_STATUS,
            permissions,
        )
        self.assertIn(
            Permission.VISION_VIEW,
            permissions,
        )
        self.assertIn(
            Permission.MEDIA_READ,
            permissions,
        )
        self.assertNotIn(
            Permission.ROBOT_DRIVE,
            permissions,
        )
        self.assertFalse(
            permissions.administration
        )

    def test_student_can_drive_robot(
        self,
    ) -> None:
        permissions = Permissions.for_role(
            Role.STUDENT
        )

        self.assertIn(
            Permission.ROBOT_DRIVE,
            permissions,
        )
        self.assertIn(
            Permission.CALIBRATION_BASIC,
            permissions,
        )
        self.assertNotIn(
            Permission.SERVICES_MANAGE,
            permissions,
        )
        self.assertFalse(
            permissions.administration
        )

    def test_teacher_has_administrative_permissions(
        self,
    ) -> None:
        permissions = Permissions.for_role(
            Role.TEACHER
        )

        self.assertIn(
            Permission.DIAGNOSTICS_READ,
            permissions,
        )
        self.assertIn(
            Permission.SERVICES_MANAGE,
            permissions,
        )
        self.assertIn(
            Permission.PLATFORM_CONFIGURE,
            permissions,
        )
        self.assertIn(
            Permission.SYSTEM_REBOOT,
            permissions,
        )
        self.assertTrue(
            permissions.administration
        )

    def test_requires_accepts_granted_permission(
        self,
    ) -> None:
        permissions = Permissions.for_role(
            Role.GUEST
        )

        permissions.requires(
            Permission.ROBOT_STATUS
        )

    def test_requires_rejects_missing_permission(
        self,
    ) -> None:
        permissions = Permissions.for_role(
            Role.GUEST
        )

        with self.assertRaises(PermissionError):
            permissions.requires(
                Permission.SYSTEM_REBOOT
            )

    def test_unknown_explicit_permissions_can_be_built(
        self,
    ) -> None:
        permissions = Permissions.from_iterable(
            {
                Permission.ROBOT_STATUS,
                Permission.ROBOT_DRIVE,
            }
        )

        self.assertEqual(
            permissions.granted,
            frozenset(
                {
                    Permission.ROBOT_STATUS,
                    Permission.ROBOT_DRIVE,
                }
            ),
        )

if __name__ == "__main__":
    unittest.main()
