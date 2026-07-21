from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import RobotCalibration
from .storage import (
    load_calibration,
    reset_calibration,
    save_calibration,
)

if TYPE_CHECKING:
    from betabox_robotics.robots.betabox_car import (
        BetaboxCar,
    )


class CalibrationManager:
    """
    Own calibration persistence for one robot.

    The manager knows where calibration is stored and
    provides a single interface for loading, saving,
    resetting, and creating a calibrated robot.

    Robot classes remain independent of files and JSON.
    """

    def __init__(
        self,
        calibration_file: Path,
    ) -> None:
        self.calibration_file = Path(
            calibration_file
        ).expanduser()

    def load(
        self,
    ) -> RobotCalibration:
        """
        Load the saved calibration.

        Missing calibration files return factory
        calibration defaults.
        """

        return load_calibration(
            self.calibration_file
        )

    def save(
        self,
        calibration: RobotCalibration,
    ) -> RobotCalibration:
        """
        Persist calibration and return the saved value.
        """

        if not isinstance(
            calibration,
            RobotCalibration,
        ):
            raise TypeError(
                "calibration must be a RobotCalibration"
            )

        save_calibration(
            self.calibration_file,
            calibration,
        )

        return calibration

    def reset(
        self,
    ) -> bool:
        """
        Remove saved calibration.

        Returns True when a saved file was removed and
        False when no saved calibration existed.
        """

        return reset_calibration(
            self.calibration_file
        )

    def exists(
        self,
    ) -> bool:
        """
        Return whether saved calibration exists.
        """

        return self.calibration_file.is_file()

    def create_car(
        self,
        **kwargs: Any,
    ) -> "BetaboxCar":
        """
        Create a BetaboxCar with the saved calibration.

        Additional keyword arguments are passed directly
        to BetaboxCar.
        """

        from betabox_robotics.robots.betabox_car import (
            BetaboxCar,
        )

        if "calibration" in kwargs:
            raise TypeError(
                "create_car manages the calibration "
                "argument automatically"
            )

        return BetaboxCar(
            calibration=self.load(),
            **kwargs,
        )
