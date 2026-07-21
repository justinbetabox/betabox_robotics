from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any

from .models import RobotCalibration


class CalibrationStorageError(
    RuntimeError
):
    """Calibration data could not be loaded or saved."""


def load_calibration(
    path: Path,
) -> RobotCalibration:
    """
    Load saved calibration.

    A missing file means the robot has not been
    calibrated yet, so factory calibration defaults
    are returned.
    """

    calibration_path = Path(
        path
    ).expanduser()

    try:
        with calibration_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            value: Any = json.load(
                file
            )
    except FileNotFoundError:
        return RobotCalibration.default()
    except json.JSONDecodeError as exc:
        raise CalibrationStorageError(
            "calibration file contains invalid JSON"
        ) from exc
    except OSError as exc:
        raise CalibrationStorageError(
            "calibration file could not be read"
        ) from exc

    try:
        return RobotCalibration.from_dict(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise CalibrationStorageError(
            "calibration file contains invalid data"
        ) from exc


def save_calibration(
    path: Path,
    calibration: RobotCalibration,
) -> None:
    """
    Save calibration atomically.

    The complete JSON document is written to a
    temporary file before replacing the current file.
    """

    calibration_path = Path(
        path
    ).expanduser()

    parent = calibration_path.parent

    temporary_path = (
        parent
        / f".{calibration_path.name}.tmp"
    )

    try:
        parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                calibration.to_dict(),
                file,
                indent=2,
                sort_keys=True,
            )

            file.write("\n")
            file.flush()
            os.fsync(
                file.fileno()
            )

        temporary_path.replace(
            calibration_path
        )
    except OSError as exc:
        try:
            temporary_path.unlink(
                missing_ok=True
            )
        except OSError:
            pass

        raise CalibrationStorageError(
            "calibration file could not be saved"
        ) from exc


def reset_calibration(
    path: Path,
) -> bool:
    """
    Remove saved calibration.

    Returns True when a file was removed and False
    when no saved calibration existed.
    """

    calibration_path = Path(
        path
    ).expanduser()

    try:
        calibration_path.unlink()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise CalibrationStorageError(
            "calibration file could not be reset"
        ) from exc

    return True
