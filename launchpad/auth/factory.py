from __future__ import annotations

from pathlib import Path

from betabox_robotics.config import PlatformConfig

from betabox_robotics.launchpad.services import (
    LaunchpadServices,
)
from betabox_robotics.services.workspace import account_by_username

from .context import LaunchpadContext
from .identity import Identity, Role
from .permissions import Permissions
from .workspace import MediaWorkspace, Workspace


def build_workspace(
    root: Path,
    *,
    persistent: bool,
) -> Workspace:
    """Build a Launchpad workspace rooted at the given directory."""

    root = root.expanduser().resolve()

    return Workspace(
        root=root,
        curriculum=root / "curriculum",
        media=MediaWorkspace(
            pictures=root / "media" / "pictures",
            videos=root / "media" / "videos",
            sounds=root / "media" / "sounds",
        ),
        preferences=root / "preferences",
        persistent=persistent,
    )


def build_guest_context(
    platform: PlatformConfig,
    services: LaunchpadServices,
) -> LaunchpadContext:
    """Build the default guest Launchpad context."""

    guest = account_by_username("guest")

    identity = Identity(
        username=guest.username,
        display_name=guest.display_name,
        role=Role.GUEST,
        authenticated=False,
    )

    workspace = build_workspace(
        guest.home,
        persistent=guest.persistent,
    )

    workspace.ensure_exists()

    permissions = Permissions(
        administration=False,
    )

    return LaunchpadContext(
        platform=platform,
        services=services,
        identity=identity,
        workspace=workspace,
        permissions=permissions,
    )
