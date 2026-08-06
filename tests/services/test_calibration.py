from __future__ import annotations

import math
import unittest
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from unittest.mock import (
    ANY,
    Mock,
    call,
    patch,
)

from betabox_robotics.calibration import (
    CalibrationManager,
    CameraMountCalibration,
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
)
from betabox_robotics.services.calibration import (
    CalibrationService,
    CalibrationStatus,
    _validate_float,
    _validate_mapping,
)

MODULE = "betabox_robotics.services.calibration"


def make_manager() -> Mock:
    return Mock(spec=CalibrationManager)


def make_calibration() -> RobotCalibration:
    return RobotCalibration()


def make_status(
    calibration: RobotCalibration | None = None,
    *,
    saved: bool = True,
) -> CalibrationStatus:
    return CalibrationStatus(
        saved=saved,
        calibration=(make_calibration() if calibration is None else calibration),
    )


class ValidateFloatTests(unittest.TestCase):
    def test_accepts_integer(self) -> None:
        result = _validate_float(
            5,
            name="offset",
        )

        self.assertEqual(
            result,
            5.0,
        )
        self.assertIsInstance(
            result,
            float,
        )

    def test_accepts_float(self) -> None:
        self.assertEqual(
            _validate_float(
                1.25,
                name="offset",
            ),
            1.25,
        )

    def test_accepts_zero(self) -> None:
        self.assertEqual(
            _validate_float(
                0,
                name="offset",
            ),
            0.0,
        )

    def test_accepts_negative_number(self) -> None:
        self.assertEqual(
            _validate_float(
                -2.5,
                name="offset",
            ),
            -2.5,
        )

    def test_rejects_boolean(self) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "offset must be a number",
                ),
            ):
                _validate_float(
                    value,
                    name="offset",
                )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            None,
            "1.5",
            object(),
            [],
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "trim must be a number",
                ),
            ):
                _validate_float(
                    value,
                    name="trim",
                )

    def test_rejects_non_finite_number(self) -> None:
        for value in (
            math.inf,
            -math.inf,
            math.nan,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "offset must be finite",
                ),
            ):
                _validate_float(
                    value,
                    name="offset",
                )


class ValidateMappingTests(unittest.TestCase):
    def test_accepts_dictionary(self) -> None:
        value: dict[str, object] = {
            "steering": {},
        }

        result = _validate_mapping(
            value,
            name="value",
        )

        self.assertIs(
            result,
            value,
        )

    def test_accepts_mapping_implementation(self) -> None:
        class ExampleMapping(Mapping[str, object]):
            def __getitem__(
                self,
                key: str,
            ) -> object:
                if key != "value":
                    raise KeyError(key)

                return 1

            def __iter__(self):
                return iter(("value",))

            def __len__(self) -> int:
                return 1

        value = ExampleMapping()

        result = _validate_mapping(
            value,
            name="value",
        )

        self.assertIs(
            result,
            value,
        )

    def test_rejects_non_mapping(self) -> None:
        for value in (
            None,
            [],
            (),
            "mapping",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "value must be a mapping",
                ),
            ):
                _validate_mapping(
                    value,
                    name="value",
                )

    def test_error_uses_supplied_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "calibration must be a mapping",
        ):
            _validate_mapping(
                None,
                name="calibration",
            )


class CalibrationStatusTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        calibration = make_calibration()

        status = CalibrationStatus(
            saved=True,
            calibration=calibration,
        )

        self.assertTrue(status.saved)
        self.assertIs(
            status.calibration,
            calibration,
        )

    def test_rejects_non_boolean_saved(self) -> None:
        for value in (
            0,
            1,
            None,
            "yes",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "saved must be a boolean",
                ),
            ):
                CalibrationStatus(
                    saved=value,  # type: ignore[arg-type]
                    calibration=make_calibration(),
                )

    def test_rejects_invalid_calibration(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("calibration must be a RobotCalibration"),
        ):
            CalibrationStatus(
                saved=True,
                calibration=object(),  # type: ignore[arg-type]
            )

    def test_to_dict(self) -> None:
        calibration = make_calibration()
        status = CalibrationStatus(
            saved=True,
            calibration=calibration,
        )

        result = status.to_dict()

        self.assertEqual(
            result["saved"],
            True,
        )
        self.assertIsInstance(
            result["calibration"],
            dict,
        )

        expected = calibration.to_dict()
        expected_grayscale = expected.get("grayscale")

        if isinstance(
            expected_grayscale,
            dict,
        ):
            expected_grayscale["calibrated"] = calibration.grayscale.calibrated

        self.assertEqual(
            result["calibration"],
            expected,
        )

    def test_to_dict_includes_grayscale_calibrated(
        self,
    ) -> None:
        calibration = make_calibration()

        status = CalibrationStatus(
            saved=False,
            calibration=calibration,
        )

        result = status.to_dict()
        calibration_dict = result["calibration"]

        self.assertIsInstance(
            calibration_dict,
            dict,
        )

        grayscale = calibration_dict.get("grayscale")

        self.assertIsInstance(
            grayscale,
            dict,
        )
        self.assertEqual(
            grayscale.get("calibrated"),
            calibration.grayscale.calibrated,
        )

    def test_to_dict_does_not_modify_calibration(
        self,
    ) -> None:
        calibration = make_calibration()
        before = calibration.to_dict()

        status = CalibrationStatus(
            saved=True,
            calibration=calibration,
        )

        status.to_dict()

        self.assertEqual(
            calibration.to_dict(),
            before,
        )

    def test_is_frozen(self) -> None:
        status = make_status()

        with self.assertRaises(FrozenInstanceError):
            status.saved = False  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        status = make_status()

        self.assertFalse(
            hasattr(
                status,
                "__dict__",
            )
        )


class CalibrationServiceInitializationTests(unittest.TestCase):
    def test_accepts_calibration_manager(self) -> None:
        manager = make_manager()

        service = CalibrationService(manager)

        self.assertIs(
            service._manager,
            manager,
        )

    def test_rejects_invalid_manager(self) -> None:
        for value in (
            None,
            object(),
            "manager",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("manager must be a CalibrationManager"),
                ),
            ):
                CalibrationService(
                    value  # type: ignore[arg-type]
                )


class CalibrationServiceStatusTests(unittest.TestCase):
    def test_returns_manager_status(self) -> None:
        manager = make_manager()
        calibration = make_calibration()

        manager.exists.return_value = True
        manager.load.return_value = calibration

        service = CalibrationService(manager)

        result = service.status()

        self.assertEqual(
            result,
            CalibrationStatus(
                saved=True,
                calibration=calibration,
            ),
        )
        manager.exists.assert_called_once_with()
        manager.load.assert_called_once_with()

    def test_preserves_unsaved_status(self) -> None:
        manager = make_manager()
        calibration = make_calibration()

        manager.exists.return_value = False
        manager.load.return_value = calibration

        result = CalibrationService(manager).status()

        self.assertFalse(result.saved)

    def test_exists_is_checked_before_load(self) -> None:
        manager = make_manager()
        parent = Mock()
        calibration = make_calibration()

        manager.exists.return_value = True
        manager.load.return_value = calibration

        parent.attach_mock(
            manager.exists,
            "exists",
        )
        parent.attach_mock(
            manager.load,
            "load",
        )

        CalibrationService(manager).status()

        self.assertEqual(
            parent.mock_calls,
            [
                call.exists(),
                call.load(),
            ],
        )

    def test_manager_error_propagates(self) -> None:
        manager = make_manager()
        error = RuntimeError("storage failure")
        manager.exists.side_effect = error

        with self.assertRaises(RuntimeError) as context:
            CalibrationService(manager).status()

        self.assertIs(
            context.exception,
            error,
        )


class CalibrationServiceLoadTests(unittest.TestCase):
    def test_delegates_to_manager(self) -> None:
        manager = make_manager()
        calibration = make_calibration()
        manager.load.return_value = calibration

        result = CalibrationService(manager).load()

        self.assertIs(
            result,
            calibration,
        )
        manager.load.assert_called_once_with()

    def test_manager_error_propagates(self) -> None:
        manager = make_manager()
        error = RuntimeError("load failed")
        manager.load.side_effect = error

        with self.assertRaises(RuntimeError) as context:
            CalibrationService(manager).load()

        self.assertIs(
            context.exception,
            error,
        )


class CalibrationServiceSaveTests(unittest.TestCase):
    def test_saves_and_returns_status(self) -> None:
        manager = make_manager()
        calibration = make_calibration()
        expected = make_status(calibration)
        service = CalibrationService(manager)

        with patch.object(
            service,
            "status",
            return_value=expected,
        ) as status:
            result = service.save(calibration)

        self.assertIs(
            result,
            expected,
        )
        manager.save.assert_called_once_with(calibration)
        status.assert_called_once_with()

    def test_rejects_invalid_calibration_before_save(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)

        with (
            patch.object(service, "status") as status,
            self.assertRaisesRegex(
                TypeError,
                ("calibration must be a RobotCalibration"),
            ),
        ):
            service.save(
                object()  # type: ignore[arg-type]
            )

        manager.save.assert_not_called()
        status.assert_not_called()

    def test_save_error_propagates(self) -> None:
        manager = make_manager()
        calibration = make_calibration()
        error = RuntimeError("save failed")
        manager.save.side_effect = error
        service = CalibrationService(manager)

        with (
            patch.object(service, "status") as status,
            self.assertRaises(RuntimeError) as context,
        ):
            service.save(calibration)

        self.assertIs(
            context.exception,
            error,
        )
        status.assert_not_called()


class CalibrationServiceSaveDictTests(unittest.TestCase):
    def test_builds_and_saves_calibration(self) -> None:
        manager = make_manager()
        service = CalibrationService(manager)
        value: dict[str, object] = {
            "steering": {
                "offset": 1.0,
            },
        }
        calibration = make_calibration()
        expected = make_status(calibration)

        with (
            patch.object(
                RobotCalibration,
                "from_dict",
                return_value=calibration,
            ) as from_dict,
            patch.object(
                service,
                "save",
                return_value=expected,
            ) as save,
        ):
            result = service.save_dict(value)

        self.assertIs(
            result,
            expected,
        )
        from_dict.assert_called_once_with(value)
        save.assert_called_once_with(calibration)

    def test_rejects_non_mapping_before_conversion(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)

        with (
            patch.object(RobotCalibration, "from_dict") as from_dict,
            patch.object(service, "save") as save,
            self.assertRaisesRegex(
                TypeError,
                "value must be a mapping",
            ),
        ):
            service.save_dict(
                []  # type: ignore[arg-type]
            )

        from_dict.assert_not_called()
        save.assert_not_called()

    def test_conversion_error_propagates(self) -> None:
        manager = make_manager()
        service = CalibrationService(manager)
        error = ValueError("invalid calibration")

        with (
            patch.object(
                RobotCalibration,
                "from_dict",
                side_effect=error,
            ),
            patch.object(service, "save") as save,
            self.assertRaises(ValueError) as context,
        ):
            service.save_dict({})

        self.assertIs(
            context.exception,
            error,
        )
        save.assert_not_called()


class CalibrationServiceUpdateSteeringTests(unittest.TestCase):
    def test_updates_only_steering(self) -> None:
        manager = make_manager()
        current = make_calibration()
        service = CalibrationService(manager)
        expected = make_status()

        with (
            patch.object(
                service,
                "load",
                return_value=current,
            ) as load,
            patch.object(
                service,
                "save",
                return_value=expected,
            ) as save,
        ):
            result = service.update_steering(2)

        self.assertIs(
            result,
            expected,
        )
        load.assert_called_once_with()
        save.assert_called_once_with(ANY)

        updated = save.call_args.args[0]

        self.assertIsInstance(
            updated,
            RobotCalibration,
        )
        self.assertEqual(
            updated.steering,
            SteeringCalibration(offset=2.0),
        )
        self.assertEqual(
            updated.camera_mount,
            current.camera_mount,
        )
        self.assertEqual(
            updated.motors,
            current.motors,
        )
        self.assertEqual(
            updated.grayscale,
            current.grayscale,
        )

    def test_rejects_invalid_offset_before_load(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)

        with (
            patch.object(service, "load") as load,
            patch.object(service, "save") as save,
            self.assertRaisesRegex(
                TypeError,
                "offset must be a number",
            ),
        ):
            service.update_steering(
                True  # type: ignore[arg-type]
            )

        load.assert_not_called()
        save.assert_not_called()


class CalibrationServiceUpdateCameraMountTests(unittest.TestCase):
    def test_updates_only_camera_mount(self) -> None:
        manager = make_manager()
        current = make_calibration()
        service = CalibrationService(manager)
        expected = make_status()

        with (
            patch.object(
                service,
                "load",
                return_value=current,
            ),
            patch.object(
                service,
                "save",
                return_value=expected,
            ) as save,
        ):
            result = service.update_camera_mount(
                pan_offset=1,
                tilt_offset=-2.5,
            )

        self.assertIs(
            result,
            expected,
        )

        updated = save.call_args.args[0]

        self.assertEqual(
            updated.camera_mount,
            CameraMountCalibration(
                pan_offset=1.0,
                tilt_offset=-2.5,
            ),
        )
        self.assertEqual(
            updated.steering,
            current.steering,
        )
        self.assertEqual(
            updated.motors,
            current.motors,
        )
        self.assertEqual(
            updated.grayscale,
            current.grayscale,
        )

    def test_validates_pan_before_tilt_and_load(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)

        with (
            patch(
                f"{MODULE}._validate_float",
                side_effect=TypeError("pan_offset must be a number"),
            ) as validate_float,
            patch.object(service, "load") as load,
            self.assertRaisesRegex(
                TypeError,
                "pan_offset must be a number",
            ),
        ):
            service.update_camera_mount(
                pan_offset=True,  # type: ignore[arg-type]
                tilt_offset=1.0,
            )

        validate_float.assert_called_once_with(
            True,
            name="pan_offset",
        )
        load.assert_not_called()

    def test_rejects_invalid_tilt_before_load(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)

        with (
            patch.object(service, "load") as load,
            self.assertRaisesRegex(
                ValueError,
                "tilt_offset must be finite",
            ),
        ):
            service.update_camera_mount(
                pan_offset=1.0,
                tilt_offset=math.inf,
            )

        load.assert_not_called()


class CalibrationServiceUpdateMotorsTests(unittest.TestCase):
    def test_updates_only_motor_calibration(
        self,
    ) -> None:
        manager = make_manager()
        current = make_calibration()
        service = CalibrationService(manager)
        expected = make_status()

        with (
            patch.object(
                service,
                "load",
                return_value=current,
            ),
            patch.object(
                service,
                "save",
                return_value=expected,
            ) as save,
        ):
            result = service.update_motors(
                left_trim=0.25,
                right_trim=0.75,
            )

        self.assertIs(
            result,
            expected,
        )

        updated = save.call_args.args[0]

        self.assertEqual(
            updated.motors,
            MotorCalibration(
                left_trim=0.25,
                right_trim=0.75,
            ),
        )
        self.assertEqual(
            updated.steering,
            current.steering,
        )
        self.assertEqual(
            updated.camera_mount,
            current.camera_mount,
        )
        self.assertEqual(
            updated.grayscale,
            current.grayscale,
        )


class CalibrationServiceUpdateGrayscaleTests(unittest.TestCase):
    def test_updates_only_grayscale(self) -> None:
        manager = make_manager()
        current = make_calibration()
        service = CalibrationService(manager)
        expected = make_status()

        with (
            patch.object(
                service,
                "load",
                return_value=current,
            ),
            patch.object(
                service,
                "save",
                return_value=expected,
            ) as save,
        ):
            result = service.update_grayscale(
                floor=[
                    100,
                    200.5,
                    300,
                ],
                line=(
                    10,
                    20,
                    30.5,
                ),
            )

        self.assertIs(
            result,
            expected,
        )

        updated = save.call_args.args[0]

        self.assertEqual(
            updated.grayscale,
            GrayscaleCalibration(
                floor=(
                    100.0,
                    200.5,
                    300.0,
                ),
                line=(
                    10.0,
                    20.0,
                    30.5,
                ),
            ),
        )
        self.assertEqual(
            updated.steering,
            current.steering,
        )
        self.assertEqual(
            updated.camera_mount,
            current.camera_mount,
        )
        self.assertEqual(
            updated.motors,
            current.motors,
        )

    def test_validates_floor_before_line_and_load(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)

        with (
            patch.object(
                service,
                "_three_values",
                side_effect=ValueError("floor must contain exactly 3 values"),
            ) as three_values,
            patch.object(service, "load") as load,
            self.assertRaisesRegex(
                ValueError,
                ("floor must contain exactly 3 values"),
            ),
        ):
            service.update_grayscale(
                floor=[
                    1,
                    2,
                ],
                line=[
                    1,
                    2,
                    3,
                ],
            )

        three_values.assert_called_once_with(
            [
                1,
                2,
            ],
            name="floor",
        )
        load.assert_not_called()

    def test_rejects_invalid_line_before_load(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)

        with (
            patch.object(service, "load") as load,
            self.assertRaisesRegex(
                TypeError,
                r"line\[1\] must be a number",
            ),
        ):
            service.update_grayscale(
                floor=[
                    1,
                    2,
                    3,
                ],
                line=[
                    1,
                    True,  # type: ignore[list-item]
                    3,
                ],
            )

        load.assert_not_called()


class CalibrationServiceClearGrayscaleTests(unittest.TestCase):
    def test_replaces_grayscale_with_default(
        self,
    ) -> None:
        manager = make_manager()
        current = make_calibration()
        service = CalibrationService(manager)
        expected = make_status()

        with (
            patch.object(
                service,
                "load",
                return_value=current,
            ) as load,
            patch.object(
                service,
                "save",
                return_value=expected,
            ) as save,
        ):
            result = service.clear_grayscale()

        self.assertIs(
            result,
            expected,
        )
        load.assert_called_once_with()

        updated = save.call_args.args[0]

        self.assertEqual(
            updated.grayscale,
            GrayscaleCalibration(),
        )
        self.assertEqual(
            updated.steering,
            current.steering,
        )
        self.assertEqual(
            updated.camera_mount,
            current.camera_mount,
        )
        self.assertEqual(
            updated.motors,
            current.motors,
        )


class CalibrationServiceResetTests(unittest.TestCase):
    def test_resets_manager_and_returns_status(
        self,
    ) -> None:
        manager = make_manager()
        service = CalibrationService(manager)
        expected = make_status(saved=False)

        with patch.object(
            service,
            "status",
            return_value=expected,
        ) as status:
            result = service.reset()

        self.assertIs(
            result,
            expected,
        )
        manager.reset.assert_called_once_with()
        status.assert_called_once_with()

    def test_reset_error_propagates(self) -> None:
        manager = make_manager()
        error = RuntimeError("reset failed")
        manager.reset.side_effect = error
        service = CalibrationService(manager)

        with (
            patch.object(service, "status") as status,
            self.assertRaises(RuntimeError) as context,
        ):
            service.reset()

        self.assertIs(
            context.exception,
            error,
        )
        status.assert_not_called()


class CalibrationServiceExistsTests(unittest.TestCase):
    def test_delegates_to_manager(self) -> None:
        manager = make_manager()
        manager.exists.return_value = True

        result = CalibrationService(manager).exists()

        self.assertTrue(result)
        manager.exists.assert_called_once_with()

    def test_preserves_false(self) -> None:
        manager = make_manager()
        manager.exists.return_value = False

        result = CalibrationService(manager).exists()

        self.assertFalse(result)


class ThreeValuesTests(unittest.TestCase):
    def test_accepts_list(self) -> None:
        self.assertEqual(
            CalibrationService._three_values(
                [
                    1,
                    2.5,
                    3,
                ],
                name="values",
            ),
            (
                1.0,
                2.5,
                3.0,
            ),
        )

    def test_accepts_tuple(self) -> None:
        self.assertEqual(
            CalibrationService._three_values(
                (
                    -1,
                    0,
                    1,
                ),
                name="values",
            ),
            (
                -1.0,
                0.0,
                1.0,
            ),
        )

    def test_rejects_string(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "floor must be a sequence",
        ):
            CalibrationService._three_values(
                "123",  # type: ignore[arg-type]
                name="floor",
            )

    def test_rejects_bytes(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "floor must be a sequence",
        ):
            CalibrationService._three_values(
                b"123",  # type: ignore[arg-type]
                name="floor",
            )

    def test_rejects_generator(self) -> None:
        values = (
            value
            for value in (
                1,
                2,
                3,
            )
        )

        with self.assertRaisesRegex(
            TypeError,
            "floor must be a sequence",
        ):
            CalibrationService._three_values(
                values,  # type: ignore[arg-type]
                name="floor",
            )

    def test_rejects_non_sequence(self) -> None:
        for value in (
            None,
            123,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "floor must be a sequence",
                ),
            ):
                CalibrationService._three_values(
                    value,  # type: ignore[arg-type]
                    name="floor",
                )

    def test_rejects_too_few_values(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("floor must contain exactly 3 values"),
        ):
            CalibrationService._three_values(
                [
                    1,
                    2,
                ],
                name="floor",
            )

    def test_rejects_too_many_values(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("line must contain exactly 3 values"),
        ):
            CalibrationService._three_values(
                [
                    1,
                    2,
                    3,
                    4,
                ],
                name="line",
            )

    def test_rejects_boolean_value(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            r"floor\[1\] must be a number",
        ):
            CalibrationService._three_values(
                [
                    1,
                    True,  # type: ignore[list-item]
                    3,
                ],
                name="floor",
            )

    def test_rejects_non_numeric_value(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            r"line\[2\] must be a number",
        ):
            CalibrationService._three_values(
                [
                    1,
                    2,
                    "3",  # type: ignore[list-item]
                ],
                name="line",
            )

    def test_rejects_non_finite_value(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"floor\[0\] must be finite",
        ):
            CalibrationService._three_values(
                [
                    math.inf,
                    2,
                    3,
                ],
                name="floor",
            )


if __name__ == "__main__":
    unittest.main()
