from __future__ import annotations

from dataclasses import dataclass

from betabox_robotics.calibration import (
    CalibrationManager,
)
from betabox_robotics.services.calibration import (
    CalibrationService,
)

from .drive_controller import ManualDriveController
from .status_cache import StatusCache


@dataclass(slots=True)
class LaunchpadServices:
    """Application services available to Launchpad requests."""

    calibration_manager: CalibrationManager
    calibration_service: CalibrationService
    status_cache: StatusCache
    drive_controller: ManualDriveController | None = None

    def require_drive_controller(
        self,
    ) -> ManualDriveController:
        """Return the active drive controller."""

        if self.drive_controller is None:
            raise RuntimeError(
                "Manual drive controller is not available"
            )

        return self.drive_controller
