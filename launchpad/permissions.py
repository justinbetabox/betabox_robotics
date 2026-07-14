from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"


class Permission(StrEnum):
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


STUDENT_PERMISSIONS = frozenset(
    {
        Permission.ROBOT_DRIVE,
        Permission.ROBOT_STATUS,
        Permission.VISION_VIEW,
        Permission.MEDIA_READ,
        Permission.CALIBRATION_BASIC,
    }
)

TEACHER_PERMISSIONS = frozenset(
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


def permissions_for_role(
    role: Role,
) -> frozenset[Permission]:
    if role is Role.TEACHER:
        return TEACHER_PERMISSIONS

    return STUDENT_PERMISSIONS


def role_has_permission(
    role: Role,
    permission: Permission,
) -> bool:
    return permission in permissions_for_role(role)
