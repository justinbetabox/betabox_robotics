from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.calibration.manager import (
    CalibrationManager,
    _validate_calibration_file,
)
from betabox_robotics.calibration.models import (
    RobotCalibration,
    SteeringCalibration,
)


class ValidateCalibrationFileTests(unittest.TestCase):
    def test_accepts_path(self) -> None:
        path = Path("/tmp/calibration.json")

        self.assertEqual(
            _validate_calibration_file(path),
            path,
        )

    def test_accepts_string(self) -> None:
        self.assertEqual(
            _validate_calibration_file("/tmp/calibration.json"),
            Path("/tmp/calibration.json"),
        )

    def test_expands_user_directory(self) -> None:
        with patch(
            "betabox_robotics.calibration.manager.Path.expanduser",
            return_value=Path("/home/picar/calibration.json"),
        ):
            result = _validate_calibration_file("~/calibration.json")

        self.assertEqual(
            result,
            Path("/home/picar/calibration.json"),
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "calibration_file must be a string or Path",
                ),
            ):
                _validate_calibration_file(value)


class CalibrationManagerConstructionTests(unittest.TestCase):
    def test_accepts_path(self) -> None:
        path = Path("/tmp/calibration.json")

        manager = CalibrationManager(path)

        self.assertEqual(
            manager.calibration_file,
            path,
        )

    def test_accepts_string(self) -> None:
        manager = CalibrationManager("/tmp/calibration.json")

        self.assertEqual(
            manager.calibration_file,
            Path("/tmp/calibration.json"),
        )

    def test_rejects_invalid_path(self) -> None:
        for value in (
            True,
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "calibration_file must be a string or Path",
                ),
            ):
                CalibrationManager(
                    value  # type: ignore[arg-type]
                )


class CalibrationManagerLoadTests(unittest.TestCase):
    def test_load_forwards_path(self) -> None:
        calibration = RobotCalibration.default()
        manager = CalibrationManager(Path("/tmp/calibration.json"))

        with patch(
            "betabox_robotics.calibration.manager.load_calibration",
            return_value=calibration,
        ) as load:
            result = manager.load()

        self.assertIs(
            result,
            calibration,
        )
        load.assert_called_once_with(manager.calibration_file)

    def test_load_propagates_storage_error(
        self,
    ) -> None:
        manager = CalibrationManager(Path("/tmp/calibration.json"))
        error = RuntimeError("load failed")

        with (
            patch(
                "betabox_robotics.calibration.manager.load_calibration",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            manager.load()

        self.assertIs(
            context.exception,
            error,
        )


class CalibrationManagerSaveTests(unittest.TestCase):
    def test_save_forwards_path_and_calibration(
        self,
    ) -> None:
        calibration = RobotCalibration(steering=SteeringCalibration(offset=4.0))
        manager = CalibrationManager(Path("/tmp/calibration.json"))

        with patch("betabox_robotics.calibration.manager.save_calibration") as save:
            result = manager.save(calibration)

        self.assertIs(
            result,
            calibration,
        )
        save.assert_called_once_with(
            manager.calibration_file,
            calibration,
        )

    def test_save_rejects_invalid_calibration(
        self,
    ) -> None:
        manager = CalibrationManager(Path("/tmp/calibration.json"))

        with (
            patch("betabox_robotics.calibration.manager.save_calibration") as save,
            self.assertRaisesRegex(
                TypeError,
                "calibration must be a RobotCalibration",
            ),
        ):
            manager.save(
                object()  # type: ignore[arg-type]
            )

        save.assert_not_called()

    def test_save_propagates_storage_error(
        self,
    ) -> None:
        manager = CalibrationManager(Path("/tmp/calibration.json"))
        calibration = RobotCalibration.default()
        error = RuntimeError("save failed")

        with (
            patch(
                "betabox_robotics.calibration.manager.save_calibration",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            manager.save(calibration)

        self.assertIs(
            context.exception,
            error,
        )


class CalibrationManagerResetTests(unittest.TestCase):
    def test_reset_returns_true(self) -> None:
        manager = CalibrationManager(Path("/tmp/calibration.json"))

        with patch(
            "betabox_robotics.calibration.manager.reset_calibration",
            return_value=True,
        ) as reset:
            result = manager.reset()

        self.assertTrue(result)
        reset.assert_called_once_with(manager.calibration_file)

    def test_reset_returns_false(self) -> None:
        manager = CalibrationManager(Path("/tmp/calibration.json"))

        with patch(
            "betabox_robotics.calibration.manager.reset_calibration",
            return_value=False,
        ):
            result = manager.reset()

        self.assertFalse(result)

    def test_reset_propagates_storage_error(
        self,
    ) -> None:
        manager = CalibrationManager(Path("/tmp/calibration.json"))
        error = RuntimeError("reset failed")

        with (
            patch(
                "betabox_robotics.calibration.manager.reset_calibration",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            manager.reset()

        self.assertIs(
            context.exception,
            error,
        )


class CalibrationManagerExistsTests(unittest.TestCase):
    def test_exists_returns_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"
            path.write_text(
                "{}",
                encoding="utf-8",
            )

            manager = CalibrationManager(path)

            self.assertTrue(manager.exists())

    def test_exists_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            manager = CalibrationManager(path)

            self.assertFalse(manager.exists())

    def test_exists_returns_false_for_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)

            manager = CalibrationManager(path)

            self.assertFalse(manager.exists())


class CalibrationManagerIntegrationTests(unittest.TestCase):
    def test_save_load_reset_lifecycle(
        self,
    ) -> None:
        calibration = RobotCalibration(steering=SteeringCalibration(offset=5.0))

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"
            manager = CalibrationManager(path)

            self.assertFalse(manager.exists())

            saved = manager.save(calibration)

            self.assertIs(
                saved,
                calibration,
            )
            self.assertTrue(manager.exists())
            self.assertEqual(
                manager.load(),
                calibration,
            )

            self.assertTrue(manager.reset())
            self.assertFalse(manager.exists())
            self.assertEqual(
                manager.load(),
                RobotCalibration.default(),
            )

            self.assertFalse(manager.reset())


if __name__ == "__main__":
    unittest.main()
