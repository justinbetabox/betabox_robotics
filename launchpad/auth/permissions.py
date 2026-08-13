from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from .identity import Role


class Permission(StrEnum):
    """Individual Launchpad capabilities."""

    ROBOT_DRIVE = "robot.drive"
    CODE = "code"
    VISION = "vision"

    MEDIA = "media"
    MEDIA_UPLOAD = "media.upload"
    MEDIA_DOWNLOAD = "media.download"
    MEDIA_DELETE = "media.delete"

    CALIBRATION = "calibration"
    STATUS = "status"
    DIAGNOSTICS = "diagnostics"
    SERVICES = "services"
    INFORMATION = "information"
    PREFERENCES = "preferences"
    EVENTS = "events"


STANDARD_PERMISSIONS: frozenset[Permission] = frozenset(Permission)

GUEST_PERMISSIONS: frozenset[Permission] = STANDARD_PERMISSIONS
STUDENT_PERMISSIONS: frozenset[Permission] = STANDARD_PERMISSIONS
TEACHER_PERMISSIONS: frozenset[Permission] = STANDARD_PERMISSIONS


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.GUEST: GUEST_PERMISSIONS,
    Role.STUDENT: STUDENT_PERMISSIONS,
    Role.TEACHER: TEACHER_PERMISSIONS,
}


def _validate_permission(
    value: object,
    *,
    name: str = "permission",
) -> Permission:
    if not isinstance(
        value,
        Permission,
    ):
        raise TypeError(f"{name} must be a Permission")

    return value


def _validate_permissions(
    value: object,
) -> frozenset[Permission]:
    if not isinstance(
        value,
        frozenset,
    ):
        raise TypeError("granted must be a frozenset")

    if not all(
        isinstance(
            permission,
            Permission,
        )
        for permission in value
    ):
        raise TypeError("granted must contain only Permission values")

    return cast(
        frozenset[Permission],
        value,
    )


@dataclass(
    slots=True,
    frozen=True,
)
class Permissions:
    """Permissions granted to the current Launchpad user."""

    granted: frozenset[Permission]

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "granted",
            _validate_permissions(self.granted),
        )

    @classmethod
    def for_role(
        cls,
        role: Role,
    ) -> Permissions:
        """Build the standard permissions for a Launchpad role."""

        return cls(granted=ROLE_PERMISSIONS[role])

    @classmethod
    def from_iterable(
        cls,
        permissions: Iterable[Permission],
    ) -> Permissions:
        """Build permissions from an explicit collection."""

        values = frozenset(permissions)

        return cls(granted=values)

    def allows(
        self,
        permission: Permission,
    ) -> bool:
        """Return whether a permission is granted."""

        permission_value = _validate_permission(permission)

        return permission_value in self.granted

    def require(
        self,
        permission: Permission,
    ) -> None:
        """Raise PermissionError when a permission is not granted."""

        permission_value = _validate_permission(permission)

        if permission_value not in self.granted:
            raise PermissionError(f"Permission required: {permission_value.value}")

    def __contains__(
        self,
        permission: object,
    ) -> bool:
        return (
            isinstance(
                permission,
                Permission,
            )
            and permission in self.granted
        )
