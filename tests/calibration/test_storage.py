from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.calibration.models import (
    CameraMountCalibration,
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
)
from betabox_robotics.calibration.storage import (
    CalibrationStorageError,
    _validate_path,
    load_calibration,
    reset_calibration,
    save_calibration,
)


class ValidatePathTests(unittest.TestCase):
    def test_accepts_path(self) -> None:
        path = Path("/tmp/calibration.json")

        self.assertEqual(
            _validate_path(path),
            path,
        )

    def test_accepts_string(self) -> None:
        self.assertEqual(
            _validate_path("/tmp/calibration.json"),
            Path("/tmp/calibration.json"),
        )

    def test_expands_user_directory(self) -> None:
        with patch(
            "betabox_robotics.calibration.storage.Path.expanduser",
            return_value=Path("/home/picar/calibration.json"),
        ):
            path = _validate_path("~/calibration.json")

        self.assertEqual(
            path,
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
                    "path must be a string or Path",
                ),
            ):
                _validate_path(value)


class LoadCalibrationTests(unittest.TestCase):
    def test_missing_file_returns_defaults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            calibration = load_calibration(path)

        self.assertEqual(
            calibration,
            RobotCalibration.default(),
        )

    def test_loads_saved_calibration(self) -> None:
        data = {
            "version": 1,
            "camera_mount": {
                "pan_offset": 2.0,
                "tilt_offset": -3.0,
            },
            "steering": {
                "offset": 4.0,
            },
            "motors": {
                "left_trim": 0.8,
                "right_trim": 0.9,
            },
            "grayscale": {
                "floor": [
                    100.0,
                    110.0,
                    120.0,
                ],
                "line": [
                    500.0,
                    510.0,
                    520.0,
                ],
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            calibration = load_calibration(path)

        self.assertEqual(
            calibration.camera_mount,
            CameraMountCalibration(
                pan_offset=2.0,
                tilt_offset=-3.0,
            ),
        )
        self.assertEqual(
            calibration.steering,
            SteeringCalibration(offset=4.0),
        )
        self.assertEqual(
            calibration.motors,
            MotorCalibration(
                left_trim=0.8,
                right_trim=0.9,
            ),
        )
        self.assertEqual(
            calibration.grayscale,
            GrayscaleCalibration(
                floor=(
                    100.0,
                    110.0,
                    120.0,
                ),
                line=(
                    500.0,
                    510.0,
                    520.0,
                ),
            ),
        )

    def test_invalid_json_raises_storage_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                "{ invalid json",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CalibrationStorageError,
                "contains invalid JSON",
            ) as context:
                load_calibration(path)

        self.assertIsInstance(
            context.exception.__cause__,
            json.JSONDecodeError,
        )

    def test_invalid_data_raises_storage_error(
        self,
    ) -> None:
        data = {
            "version": 1,
            "steering": {
                "offset": 100,
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CalibrationStorageError,
                "contains invalid data",
            ) as context:
                load_calibration(path)

        self.assertIsInstance(
            context.exception.__cause__,
            ValueError,
        )

    def test_non_object_json_raises_storage_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                json.dumps(
                    [
                        1,
                        2,
                        3,
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CalibrationStorageError,
                "contains invalid data",
            ) as context:
                load_calibration(path)

        self.assertIsInstance(
            context.exception.__cause__,
            TypeError,
        )

    def test_read_os_error_is_wrapped(
        self,
    ) -> None:
        with (
            patch(
                "betabox_robotics.calibration.storage.Path.open",
                side_effect=PermissionError("permission denied"),
            ),
            self.assertRaisesRegex(
                CalibrationStorageError,
                "could not be read",
            ) as context,
        ):
            load_calibration(Path("/tmp/calibration.json"))

        self.assertIsInstance(
            context.exception.__cause__,
            PermissionError,
        )

    def test_accepts_string_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                json.dumps(RobotCalibration.default().to_dict()),
                encoding="utf-8",
            )

            calibration = load_calibration(str(path))

        self.assertEqual(
            calibration,
            RobotCalibration.default(),
        )


class SaveCalibrationTests(unittest.TestCase):
    def test_saves_calibration(self) -> None:
        calibration = RobotCalibration(
            camera_mount=CameraMountCalibration(
                pan_offset=2.0,
                tilt_offset=-3.0,
            ),
            steering=SteeringCalibration(offset=4.0),
            motors=MotorCalibration(
                left_trim=0.8,
                right_trim=0.9,
            ),
            grayscale=GrayscaleCalibration(
                floor=(
                    100.0,
                    110.0,
                    120.0,
                ),
                line=(
                    500.0,
                    510.0,
                    520.0,
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested" / "calibration.json"

            save_calibration(
                path,
                calibration,
            )

            self.assertTrue(path.is_file())

            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            saved,
            {
                "version": 1,
                "camera_mount": {
                    "pan_offset": 2.0,
                    "tilt_offset": -3.0,
                },
                "steering": {
                    "offset": 4.0,
                },
                "motors": {
                    "left_trim": 0.8,
                    "right_trim": 0.9,
                },
                "grayscale": {
                    "floor": [
                        100.0,
                        110.0,
                        120.0,
                    ],
                    "line": [
                        500.0,
                        510.0,
                        520.0,
                    ],
                },
            },
        )

    def test_saved_file_ends_with_newline(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            save_calibration(
                path,
                RobotCalibration.default(),
            )

            content = path.read_text(encoding="utf-8")

        self.assertTrue(content.endswith("\n"))

    def test_saved_file_can_be_loaded(
        self,
    ) -> None:
        calibration = RobotCalibration(steering=SteeringCalibration(offset=5.0))

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            save_calibration(
                path,
                calibration,
            )

            loaded = load_calibration(path)

        self.assertEqual(
            loaded,
            calibration,
        )

    def test_overwrites_existing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                "old data",
                encoding="utf-8",
            )

            calibration = RobotCalibration(steering=SteeringCalibration(offset=3.0))

            save_calibration(
                path,
                calibration,
            )

            loaded = load_calibration(path)

        self.assertEqual(
            loaded,
            calibration,
        )

    def test_rejects_invalid_calibration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "calibration must be a RobotCalibration",
        ):
            save_calibration(
                Path("/tmp/calibration.json"),
                object(),  # type: ignore[arg-type]
            )

    def test_directory_creation_error_is_wrapped(
        self,
    ) -> None:
        with (
            patch(
                "betabox_robotics.calibration.storage.Path.mkdir",
                side_effect=PermissionError("permission denied"),
            ),
            self.assertRaisesRegex(
                CalibrationStorageError,
                "could not be saved",
            ) as context,
        ):
            save_calibration(
                Path("/tmp/calibration.json"),
                RobotCalibration.default(),
            )

        self.assertIsInstance(
            context.exception.__cause__,
            PermissionError,
        )

    def test_temporary_file_creation_error_is_wrapped(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.calibration.storage.Path.mkdir"),
            patch(
                "betabox_robotics.calibration.storage.tempfile.NamedTemporaryFile",
                side_effect=OSError("temporary file failed"),
            ),
            self.assertRaisesRegex(
                CalibrationStorageError,
                "could not be saved",
            ) as context,
        ):
            save_calibration(
                Path("/tmp/calibration.json"),
                RobotCalibration.default(),
            )

        self.assertIsInstance(
            context.exception.__cause__,
            OSError,
        )

    def test_json_serialization_error_is_wrapped(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch(
                "betabox_robotics.calibration.storage.json.dump",
                side_effect=TypeError("serialization failed"),
            ),
        ):
            path = Path(temp_dir) / "calibration.json"

            with self.assertRaisesRegex(
                CalibrationStorageError,
                "could not be saved",
            ) as context:
                save_calibration(
                    path,
                    RobotCalibration.default(),
                )

            temporary_files = list(Path(temp_dir).glob(".calibration.json.*.tmp"))

        self.assertIsInstance(
            context.exception.__cause__,
            TypeError,
        )
        self.assertEqual(
            temporary_files,
            [],
        )

    def test_replace_error_is_wrapped_and_temp_removed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            original_replace = Path.replace

            def fail_destination_replace(
                temporary_path: Path,
                target: Path,
            ) -> Path:
                if target == path:
                    raise OSError("replace failed")

                return original_replace(
                    temporary_path,
                    target,
                )

            with (
                patch(
                    "betabox_robotics.calibration.storage.Path.replace",
                    autospec=True,
                    side_effect=fail_destination_replace,
                ),
                self.assertRaisesRegex(
                    CalibrationStorageError,
                    "could not be saved",
                ),
            ):
                save_calibration(
                    path,
                    RobotCalibration.default(),
                )

            temporary_files = list(Path(temp_dir).glob(".calibration.json.*.tmp"))

        self.assertEqual(
            temporary_files,
            [],
        )

    def test_fsync_is_called(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("betabox_robotics.calibration.storage.os.fsync") as fsync,
        ):
            path = Path(temp_dir) / "calibration.json"

            save_calibration(
                path,
                RobotCalibration.default(),
            )

        fsync.assert_called_once()

    def test_accepts_string_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            save_calibration(
                str(path),
                RobotCalibration.default(),
            )

            self.assertTrue(path.is_file())


class ResetCalibrationTests(unittest.TestCase):
    def test_removes_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                "{}",
                encoding="utf-8",
            )

            removed = reset_calibration(path)

            self.assertTrue(removed)
            self.assertFalse(path.exists())

    def test_missing_file_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            removed = reset_calibration(path)

        self.assertFalse(removed)

    def test_unlink_error_is_wrapped(self) -> None:
        with (
            patch(
                "betabox_robotics.calibration.storage.Path.unlink",
                side_effect=PermissionError("permission denied"),
            ),
            self.assertRaisesRegex(
                CalibrationStorageError,
                "could not be reset",
            ) as context,
        ):
            reset_calibration(Path("/tmp/calibration.json"))

        self.assertIsInstance(
            context.exception.__cause__,
            PermissionError,
        )

    def test_accepts_string_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"

            path.write_text(
                "{}",
                encoding="utf-8",
            )

            removed = reset_calibration(str(path))

        self.assertTrue(removed)


if __name__ == "__main__":
    unittest.main()
