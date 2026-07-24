from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from .identity import Role


class Permission(StrEnum):
    """Individual Launchpad capabilities."""

    ROBOT_DRIVE = "robot.drive"
    CODE = "code"
    VISION = "vision"

    MEDIA = "media"
    MEDIA_UPLOAD = "media.upload"
    MEDIA_DOWNLOAD = "media.download"

    CALIBRATION = "calibration"
    STATUS = "status"
    DIAGNOSTICS = "diagnostics"
    SERVICES = "services"
    INFORMATION = "information"
    PREFERENCES = "preferences"
    EVENTS = "events"


STANDARD_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.ROBOT_DRIVE,
        Permission.CODE,
        Permission.VISION,
        Permission.MEDIA,
        Permission.MEDIA_UPLOAD,
        Permission.MEDIA_DOWNLOAD,
        Permission.CALIBRATION,
        Permission.STATUS,
        Permission.DIAGNOSTICS,
        Permission.SERVICES,
        Permission.INFORMATION,
        Permission.PREFERENCES,
        Permission.EVENTS,
    }
)

GUEST_PERMISSIONS = STANDARD_PERMISSIONS
STUDENT_PERMISSIONS = STANDARD_PERMISSIONS
TEACHER_PERMISSIONS = STANDARD_PERMISSIONS


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

    def require(
        self,
        permission: Permission,
    ) -> None:
        """Raise PermissionError when a permission is not granted."""

        if not self.allows(permission):
            raise PermissionError(f"Permission required: {permission.value}")

    def __contains__(
        self,
        permission: object,
    ) -> bool:
        return permission in self.granted
