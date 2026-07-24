from __future__ import annotations

from dataclasses import dataclass

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.services import (
    LaunchpadServices,
)

from .identity import Identity, Role
from .permissions import Permission, Permissions
from .workspace import Workspace


@dataclass(slots=True, frozen=True)
class LaunchpadContext:
    """Current Launchpad execution context."""

    platform: PlatformConfig
    services: LaunchpadServices
    identity: Identity
    workspace: Workspace
    permissions: Permissions

    def can(
        self,
        permission: Permission,
    ) -> bool:
        """Return whether the current user has a permission."""

        return self.permissions.allows(permission)

    def require(
        self,
        permission: Permission,
    ) -> None:
        """Require a permission for the current operation."""

        self.permissions.requires(permission)

    @property
    def guest(self) -> bool:
        """Whether the current user has the guest role."""

        return self.identity.role is Role.GUEST

    @property
    def student(self) -> bool:
        """Whether the current user has the student role."""

        return self.identity.role is Role.STUDENT

    @property
    def teacher(self) -> bool:
        """Whether the current user has the teacher role."""

        return self.identity.role is Role.TEACHER

    @property
    def authenticated(self) -> bool:
        """Whether the current identity is authenticated."""

        return self.identity.authenticated

    @property
    def persistent_workspace(self) -> bool:
        """Whether the current workspace persists between sessions."""

        return self.workspace.persistent
