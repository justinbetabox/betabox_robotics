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
    Role,
    build_guest_context,
    build_workspace,
    LaunchpadContext,
    LaunchpadContextProvider,
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

        context = build_guest_context(
            platform,
            create_test_services(),
            workspace_root=Path(
                "/tmp/betabox-test-guest"
            ),
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

        context = build_guest_context(
            platform,
            create_test_services(),
            workspace_root=Path(
                "/tmp/betabox-test-guest"
            ),
        )

        self.assertFalse(
            context.workspace.persistent
        )
        self.assertFalse(
            context.permissions.administration
        )


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

if __name__ == "__main__":
    unittest.main()
