from __future__ import annotations

from pathlib import Path

from .models import RobotCalibration
from .storage import (
    load_calibration,
    reset_calibration,
    save_calibration,
)


def _validate_calibration_file(
    value: object,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError("calibration_file must be a string or Path")

    return Path(value).expanduser()


class CalibrationManager:
    """
    Manage calibration persistence for one robot workspace.

    The manager owns the location of the calibration file and provides
    one interface for loading, saving, resetting, and checking saved
    calibration. It does not construct robots or access hardware.
    """

    def __init__(
        self,
        calibration_file: str | Path,
    ) -> None:
        self.calibration_file = _validate_calibration_file(calibration_file)

    def load(
        self,
    ) -> RobotCalibration:
        """
        Load saved calibration.

        Missing calibration files return factory calibration defaults.
        """

        return load_calibration(self.calibration_file)

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
            raise TypeError("calibration must be a RobotCalibration")

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

        Returns True when a saved file was removed and False when no
        saved calibration existed.
        """

        return reset_calibration(self.calibration_file)

    def exists(
        self,
    ) -> bool:
        """
        Return whether saved calibration exists.
        """

        return self.calibration_file.is_file()
