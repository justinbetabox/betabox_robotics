from __future__ import annotations

from dataclasses import dataclass

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.services import (
    LaunchpadServices,
)

from .identity import Identity
from .permissions import Permissions
from .workspace import Workspace


@dataclass(slots=True, frozen=True)
class LaunchpadContext:
    """Current Launchpad execution context."""

    platform: PlatformConfig
    services: LaunchpadServices

    identity: Identity
    workspace: Workspace
    permissions: Permissions

    @property
    def guest(self) -> bool:
        return self.identity.guest

    @property
    def persistent_workspace(self) -> bool:
        return self.workspace.persistent
