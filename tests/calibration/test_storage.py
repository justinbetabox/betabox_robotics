from __future__ import annotations

import json
import tempfile
import unittest

from pathlib import Path

from betabox_robotics.calibration import (
    CalibrationStorageError,
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
    load_calibration,
    reset_calibration,
    save_calibration,
)


class CalibrationModelTests(
    unittest.TestCase
):
    def test_defaults(
        self,
    ) -> None:
        calibration = (
            RobotCalibration.default()
        )

        self.assertEqual(
            calibration.steering.offset,
            0.0,
        )

        self.assertEqual(
            calibration.motors.left_trim,
            1.0,
        )

        self.assertEqual(
            calibration.motors.right_trim,
            1.0,
        )

        self.assertFalse(
            calibration.grayscale.calibrated
        )

    def test_rejects_invalid_motor_trim(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            MotorCalibration(
                left_trim=1.1
            )

    def test_rejects_partial_grayscale_calibration(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            GrayscaleCalibration(
                floor=(
                    1000,
                    1000,
                    1000,
                ),
                line=None,
            )


class CalibrationStorageTests(
    unittest.TestCase
):
    def test_missing_file_returns_defaults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "calibration.json"
            )

            calibration = load_calibration(
                path
            )

            self.assertEqual(
                calibration,
                RobotCalibration.default(),
            )

    def test_save_and_load(
        self,
    ) -> None:
        calibration = RobotCalibration(
            steering=SteeringCalibration(
                offset=2.5
            ),
            motors=MotorCalibration(
                left_trim=0.95,
                right_trim=1.0,
            ),
            grayscale=GrayscaleCalibration(
                floor=(
                    900,
                    910,
                    920,
                ),
                line=(
                    250,
                    260,
                    270,
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "state"
                / "calibration.json"
            )

            save_calibration(
                path,
                calibration,
            )

            loaded = load_calibration(
                path
            )

            self.assertEqual(
                loaded,
                calibration,
            )

    def test_saved_json_is_readable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "calibration.json"
            )

            save_calibration(
                path,
                RobotCalibration.default(),
            )

            value = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                value["version"],
                1,
            )

            self.assertIn(
                "steering",
                value,
            )

            self.assertIn(
                "motors",
                value,
            )

            self.assertIn(
                "grayscale",
                value,
            )

    def test_invalid_json_raises_storage_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "calibration.json"
            )

            path.write_text(
                "{not valid json",
                encoding="utf-8",
            )

            with self.assertRaises(
                CalibrationStorageError
            ):
                load_calibration(
                    path
                )

    def test_reset_removes_saved_calibration(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "calibration.json"
            )

            save_calibration(
                path,
                RobotCalibration.default(),
            )

            self.assertTrue(
                reset_calibration(
                    path
                )
            )

            self.assertFalse(
                path.exists()
            )

            self.assertFalse(
                reset_calibration(
                    path
                )
            )


if __name__ == "__main__":
    unittest.main()
