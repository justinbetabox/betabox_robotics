from __future__ import annotations

import pwd

from pathlib import Path

from betabox_robotics.config import PlatformConfig

from betabox_robotics.launchpad.services import (
    LaunchpadServices,
)

from .context import LaunchpadContext
from .identity import Identity, Role
from .permissions import Permissions
from .workspace import MediaWorkspace, Workspace


def account_home(
    username: str,
) -> Path:
    """Return the configured home directory for a Linux account."""

    try:
        account = pwd.getpwnam(
            username
        )
    except KeyError as exc:
        raise RuntimeError(
            f"Linux account does not exist: {username}"
        ) from exc

    return Path(
        account.pw_dir
    ).expanduser().resolve()


def build_workspace(
    root: Path,
    *,
    persistent: bool,
) -> Workspace:
    """Build a Launchpad workspace rooted at the given directory."""

    root = Path(
        root
    ).expanduser().resolve()

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


def build_account_workspace(
    username: str,
    *,
    persistent: bool,
) -> Workspace:
    """Build a workspace from a Linux account."""

    return build_workspace(
        account_home(username),
        persistent=persistent,
    )


def build_guest_context(
    platform: PlatformConfig,
    services: LaunchpadServices,
) -> LaunchpadContext:
    """Build the default guest Launchpad context."""

    identity = Identity(
        username="guest",
        display_name="Guest",
        role=Role.GUEST,
        authenticated=False,
    )

    workspace = build_account_workspace(
        "guest",
        persistent=False,
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
