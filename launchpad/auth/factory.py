from __future__ import annotations

from pathlib import Path

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.services import (
    LaunchpadServices,
)
from betabox_robotics.services.accounts import (
    account_by_username,
)

from .context import LaunchpadContext
from .identity import Identity, Role
from .permissions import Permissions
from .workspace import build_workspace


def role_for_username(
    username: str,
) -> Role:
    """Return the Launchpad role for a managed username."""

    if username == "guest":
        return Role.GUEST

    return Role.STUDENT


def build_account_context(
    platform: PlatformConfig,
    services: LaunchpadServices,
    username: str,
    *,
    workspace_root: Path | None = None,
) -> LaunchpadContext:
    """Build a Launchpad context for a managed account."""

    account = account_by_username(username)
    role = role_for_username(account.username)

    identity = Identity(
        username=account.username,
        display_name=account.display_name,
        role=role,
        authenticated=role is not Role.GUEST,
    )

    root = account.home if workspace_root is None else workspace_root

    workspace = build_workspace(
        root,
        persistent=account.persistent,
    )
    workspace.ensure_exists()

    return LaunchpadContext(
        platform=platform,
        services=services,
        identity=identity,
        workspace=workspace,
        permissions=Permissions.for_role(role),
    )


def build_guest_context(
    platform: PlatformConfig,
    services: LaunchpadServices,
    *,
    workspace_root: Path | None = None,
) -> LaunchpadContext:
    """Build the default guest Launchpad context."""

    return build_account_context(
        platform,
        services,
        "guest",
        workspace_root=workspace_root,
    )
