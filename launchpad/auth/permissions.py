from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .identity import Role


class Permission(StrEnum):
    """Individual Launchpad capabilities."""

    ROBOT_DRIVE = "robot.drive"
    ROBOT_STATUS = "robot.status"
    VISION_VIEW = "vision.view"
    MEDIA_READ = "media.read"
    CALIBRATION_BASIC = "calibration.basic"

    DIAGNOSTICS_READ = "diagnostics.read"
    VERIFICATION_RUN = "verification.run"
    SERVICES_MANAGE = "services.manage"
    MEDIA_MANAGE = "media.manage"
    CALIBRATION_ADVANCED = "calibration.advanced"
    RECOVERY_BACKUP = "recovery.backup"
    RECOVERY_RESTORE = "recovery.restore"
    RECOVERY_RESET = "recovery.reset"
    PLATFORM_CONFIGURE = "platform.configure"
    SYSTEM_REBOOT = "system.reboot"


GUEST_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.ROBOT_STATUS,
        Permission.VISION_VIEW,
        Permission.MEDIA_READ,
    }
)

STUDENT_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        *GUEST_PERMISSIONS,
        Permission.ROBOT_DRIVE,
        Permission.CALIBRATION_BASIC,
    }
)

TEACHER_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        *STUDENT_PERMISSIONS,
        Permission.DIAGNOSTICS_READ,
        Permission.VERIFICATION_RUN,
        Permission.SERVICES_MANAGE,
        Permission.MEDIA_MANAGE,
        Permission.CALIBRATION_ADVANCED,
        Permission.RECOVERY_BACKUP,
        Permission.RECOVERY_RESTORE,
        Permission.RECOVERY_RESET,
        Permission.PLATFORM_CONFIGURE,
        Permission.SYSTEM_REBOOT,
    }
)


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.GUEST: GUEST_PERMISSIONS,
    Role.STUDENT: STUDENT_PERMISSIONS,
    Role.TEACHER: TEACHER_PERMISSIONS,
}


@dataclass(slots=True, frozen=True)
class Permissions:
    """Permissions granted to the current Launchpad user."""

    granted: frozenset[Permission]

    @classmethod
    def for_role(
        cls,
        role: Role,
    ) -> Permissions:
        """Build the standard permissions for a Launchpad role."""

        return cls(
            granted=ROLE_PERMISSIONS.get(
                role,
                frozenset(),
            )
        )

    @classmethod
    def from_iterable(
        cls,
        permissions: Iterable[Permission],
    ) -> Permissions:
        """Build permissions from an explicit collection."""

        return cls(granted=frozenset(permissions))

    def allows(
        self,
        permission: Permission,
    ) -> bool:
        """Return whether a permission is granted."""

        return permission in self.granted

    def requires(
        self,
        permission: Permission,
    ) -> None:
        """Raise PermissionError when a permission is not granted."""

        if not self.allows(permission):
            raise PermissionError(
                f"Permission required: {permission.value}"
            )

    def __contains__(
        self,
        permission: object,
    ) -> bool:
        return permission in self.granted

    @property
    def administration(self) -> bool:
        """Whether administrative Launchpad access is granted."""

        return self.allows(
            Permission.PLATFORM_CONFIGURE
        )
