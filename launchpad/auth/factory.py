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


def _validate_username(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("username must be a string")

    result = value.strip()

    if not result:
        raise ValueError("username cannot be empty")

    return result


def _validate_platform(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("platform must be a PlatformConfig")

    return value


def _validate_services(
    value: object,
) -> LaunchpadServices:
    if not isinstance(
        value,
        LaunchpadServices,
    ):
        raise TypeError("services must be LaunchpadServices")

    return value


def _validate_workspace_root(
    value: object,
) -> Path | None:
    if value is None:
        return None

    if not isinstance(
        value,
        Path,
    ):
        raise TypeError("workspace_root must be a Path or None")

    return value


def role_for_username(
    username: str,
) -> Role:
    """Return the Launchpad role for a managed username."""

    username_value = _validate_username(username)

    if username_value == "guest":
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

    platform_value = _validate_platform(platform)
    services_value = _validate_services(services)
    username_value = _validate_username(username)
    workspace_root_value = _validate_workspace_root(workspace_root)

    account = account_by_username(username_value)
    role = role_for_username(account.username)

    identity = Identity(
        username=account.username,
        display_name=account.display_name,
        role=role,
        authenticated=(role is not Role.GUEST),
    )

    root = account.home if workspace_root_value is None else workspace_root_value

    workspace = build_workspace(
        root,
        persistent=account.persistent,
    )
    workspace.ensure_exists()

    return LaunchpadContext(
        platform=platform_value,
        services=services_value,
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
