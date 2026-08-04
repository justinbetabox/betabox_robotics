from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.calibration.models import (
    CALIBRATION_VERSION,
    CameraMountCalibration,
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
    _float_value,
    _int_value,
    _mapping_value,
    _three_values,
)


class FloatValueTests(unittest.TestCase):
    def test_accepts_integer(self) -> None:
        self.assertEqual(
            _float_value(
                4,
                field_name="value",
            ),
            4.0,
        )

    def test_accepts_float(self) -> None:
        self.assertEqual(
            _float_value(
                4.5,
                field_name="value",
            ),
            4.5,
        )

    def test_accepts_numeric_string(self) -> None:
        self.assertEqual(
            _float_value(
                " 4.5 ",
                field_name="value",
            ),
            4.5,
        )

    def test_uses_default(self) -> None:
        self.assertEqual(
            _float_value(
                None,
                field_name="value",
                default=3.5,
            ),
            3.5,
        )

    def test_rejects_none_without_default(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be a number",
        ):
            _float_value(
                None,
                field_name="value",
            )

    def test_rejects_boolean(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be a number",
        ):
            _float_value(
                True,
                field_name="value",
            )

    def test_rejects_invalid_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be a number",
        ):
            _float_value(
                object(),
                field_name="value",
            )

    def test_rejects_invalid_string(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be a number",
        ):
            _float_value(
                "not-a-number",
                field_name="value",
            )

    def test_rejects_non_finite_values(self) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
            "nan",
            "inf",
            "-inf",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be finite",
                ),
            ):
                _float_value(
                    value,
                    field_name="value",
                )


class IntValueTests(unittest.TestCase):
    def test_accepts_integer(self) -> None:
        self.assertEqual(
            _int_value(
                4,
                field_name="value",
            ),
            4,
        )

    def test_accepts_integral_float(self) -> None:
        self.assertEqual(
            _int_value(
                4.0,
                field_name="value",
            ),
            4,
        )

    def test_accepts_integral_string(self) -> None:
        self.assertEqual(
            _int_value(
                " 4 ",
                field_name="value",
            ),
            4,
        )

    def test_accepts_integral_decimal_string(self) -> None:
        self.assertEqual(
            _int_value(
                "4.0",
                field_name="value",
            ),
            4,
        )

    def test_uses_default(self) -> None:
        self.assertEqual(
            _int_value(
                None,
                field_name="value",
                default=3,
            ),
            3,
        )

    def test_rejects_none_without_default(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be an integer",
        ):
            _int_value(
                None,
                field_name="value",
            )

    def test_rejects_boolean(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be an integer",
        ):
            _int_value(
                True,
                field_name="value",
            )

    def test_rejects_invalid_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be an integer",
        ):
            _int_value(
                object(),
                field_name="value",
            )

    def test_rejects_non_integral_float(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be an integer",
        ):
            _int_value(
                4.5,
                field_name="value",
            )

    def test_rejects_non_integral_string(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be an integer",
        ):
            _int_value(
                "4.5",
                field_name="value",
            )

    def test_rejects_blank_string(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be an integer",
        ):
            _int_value(
                " ",
                field_name="value",
            )

    def test_rejects_invalid_string(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must be an integer",
        ):
            _int_value(
                "invalid",
                field_name="value",
            )

    def test_rejects_non_finite_values(self) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
            "nan",
            "inf",
            "-inf",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be an integer",
                ),
            ):
                _int_value(
                    value,
                    field_name="value",
                )


class ThreeValuesTests(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(
            _three_values(
                None,
                field_name="values",
            )
        )

    def test_accepts_tuple(self) -> None:
        self.assertEqual(
            _three_values(
                (
                    1,
                    2.5,
                    "3",
                ),
                field_name="values",
            ),
            (
                1.0,
                2.5,
                3.0,
            ),
        )

    def test_accepts_list(self) -> None:
        self.assertEqual(
            _three_values(
                [
                    1,
                    2,
                    3,
                ],
                field_name="values",
            ),
            (
                1.0,
                2.0,
                3.0,
            ),
        )

    def test_rejects_wrong_length(self) -> None:
        for value in (
            (),
            (1,),
            (
                1,
                2,
            ),
            (
                1,
                2,
                3,
                4,
            ),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "values must contain exactly 3 values",
                ),
            ):
                _three_values(
                    value,
                    field_name="values",
                )

    def test_rejects_string_like_values(self) -> None:
        for value in (
            "123",
            b"123",
            bytearray(b"123"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "values must contain exactly 3 values",
                ),
            ):
                _three_values(
                    value,
                    field_name="values",
                )

    def test_rejects_invalid_item(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "values value must be a number",
        ):
            _three_values(
                (
                    1,
                    object(),
                    3,
                ),
                field_name="values",
            )


class MappingValueTests(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(
            _mapping_value(
                None,
                field_name="value",
            )
        )

    def test_accepts_mapping(self) -> None:
        value = {
            "key": "value",
        }

        self.assertIs(
            _mapping_value(
                value,
                field_name="value",
            ),
            value,
        )

    def test_rejects_non_mapping(self) -> None:
        for value in (
            [],
            (),
            "value",
            1,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "value must be an object",
                ),
            ):
                _mapping_value(
                    value,
                    field_name="value",
                )


class SteeringCalibrationTests(unittest.TestCase):
    def test_defaults(self) -> None:
        calibration = SteeringCalibration()

        self.assertEqual(
            calibration.offset,
            0.0,
        )
        self.assertFalse(calibration.adjusted)

    def test_accepts_valid_offset(self) -> None:
        calibration = SteeringCalibration(
            offset=5,
        )

        self.assertEqual(
            calibration.offset,
            5.0,
        )
        self.assertTrue(calibration.adjusted)

    def test_accepts_boundary_offsets(self) -> None:
        for value in (
            -30,
            30,
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    SteeringCalibration(offset=value).offset,
                    float(value),
                )

    def test_rejects_offset_outside_range(self) -> None:
        for value in (
            -30.1,
            30.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "steering offset must be between",
                ),
            ):
                SteeringCalibration(offset=value)

    def test_from_dict_none_returns_default(
        self,
    ) -> None:
        self.assertEqual(
            SteeringCalibration.from_dict(None),
            SteeringCalibration(),
        )

    def test_from_dict_empty_returns_default(
        self,
    ) -> None:
        self.assertEqual(
            SteeringCalibration.from_dict({}),
            SteeringCalibration(),
        )

    def test_from_dict(self) -> None:
        calibration = SteeringCalibration.from_dict(
            {
                "offset": "4.5",
            }
        )

        self.assertEqual(
            calibration.offset,
            4.5,
        )

    def test_from_dict_rejects_non_mapping(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "steering calibration must be an object",
        ):
            SteeringCalibration.from_dict(
                []  # type: ignore[arg-type]
            )


class MotorCalibrationTests(unittest.TestCase):
    def test_defaults(self) -> None:
        calibration = MotorCalibration()

        self.assertEqual(
            calibration.left_trim,
            1.0,
        )
        self.assertEqual(
            calibration.right_trim,
            1.0,
        )
        self.assertFalse(calibration.adjusted)

    def test_accepts_valid_trims(self) -> None:
        calibration = MotorCalibration(
            left_trim=0.8,
            right_trim=0.9,
        )

        self.assertEqual(
            calibration.left_trim,
            0.8,
        )
        self.assertEqual(
            calibration.right_trim,
            0.9,
        )
        self.assertTrue(calibration.adjusted)

    def test_accepts_boundary_trims(self) -> None:
        calibration = MotorCalibration(
            left_trim=0,
            right_trim=1,
        )

        self.assertEqual(
            calibration.left_trim,
            0.0,
        )
        self.assertEqual(
            calibration.right_trim,
            1.0,
        )

    def test_rejects_trims_outside_range(
        self,
    ) -> None:
        for field_name in (
            "left_trim",
            "right_trim",
        ):
            for value in (
                -0.1,
                1.1,
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(ValueError),
                ):
                    kwargs: dict[str, object] = {
                        "left_trim": 1.0,
                        "right_trim": 1.0,
                    }
                    kwargs[field_name] = value

                    MotorCalibration(
                        **kwargs  # type: ignore[arg-type]
                    )

    def test_from_dict_none_returns_default(
        self,
    ) -> None:
        self.assertEqual(
            MotorCalibration.from_dict(None),
            MotorCalibration(),
        )

    def test_from_dict(self) -> None:
        calibration = MotorCalibration.from_dict(
            {
                "left_trim": "0.75",
                "right_trim": 0.9,
            }
        )

        self.assertEqual(
            calibration.left_trim,
            0.75,
        )
        self.assertEqual(
            calibration.right_trim,
            0.9,
        )

    def test_from_dict_rejects_non_mapping(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "motor calibration must be an object",
        ):
            MotorCalibration.from_dict(
                []  # type: ignore[arg-type]
            )


class CameraMountCalibrationTests(unittest.TestCase):
    def test_defaults(self) -> None:
        calibration = CameraMountCalibration()

        self.assertEqual(
            calibration.pan_offset,
            0.0,
        )
        self.assertEqual(
            calibration.tilt_offset,
            0.0,
        )
        self.assertFalse(calibration.adjusted)

    def test_accepts_valid_offsets(self) -> None:
        calibration = CameraMountCalibration(
            pan_offset=5,
            tilt_offset=-4,
        )

        self.assertEqual(
            calibration.pan_offset,
            5.0,
        )
        self.assertEqual(
            calibration.tilt_offset,
            -4.0,
        )
        self.assertTrue(calibration.adjusted)

    def test_rejects_offsets_outside_range(
        self,
    ) -> None:
        for field_name in (
            "pan_offset",
            "tilt_offset",
        ):
            for value in (
                -30.1,
                30.1,
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(ValueError),
                ):
                    kwargs: dict[str, object] = {
                        "pan_offset": 0.0,
                        "tilt_offset": 0.0,
                    }
                    kwargs[field_name] = value

                    CameraMountCalibration(
                        **kwargs  # type: ignore[arg-type]
                    )

    def test_from_dict_none_returns_default(
        self,
    ) -> None:
        self.assertEqual(
            CameraMountCalibration.from_dict(None),
            CameraMountCalibration(),
        )

    def test_from_dict(self) -> None:
        calibration = CameraMountCalibration.from_dict(
            {
                "pan_offset": "3",
                "tilt_offset": -2,
            }
        )

        self.assertEqual(
            calibration.pan_offset,
            3.0,
        )
        self.assertEqual(
            calibration.tilt_offset,
            -2.0,
        )

    def test_from_dict_rejects_non_mapping(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "camera mount calibration must be an object",
        ):
            CameraMountCalibration.from_dict(
                []  # type: ignore[arg-type]
            )


class GrayscaleCalibrationTests(unittest.TestCase):
    def test_defaults(self) -> None:
        calibration = GrayscaleCalibration()

        self.assertIsNone(calibration.floor)
        self.assertIsNone(calibration.line)
        self.assertFalse(calibration.calibrated)

    def test_accepts_floor_and_line(self) -> None:
        calibration = GrayscaleCalibration(
            floor=(
                100,
                110,
                120,
            ),
            line=(
                500,
                510,
                520,
            ),
        )

        self.assertEqual(
            calibration.floor,
            (
                100.0,
                110.0,
                120.0,
            ),
        )
        self.assertEqual(
            calibration.line,
            (
                500.0,
                510.0,
                520.0,
            ),
        )
        self.assertTrue(calibration.calibrated)

    def test_rejects_floor_without_line(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "both be set or both be empty",
        ):
            GrayscaleCalibration(
                floor=(
                    1,
                    2,
                    3,
                ),
            )

    def test_rejects_line_without_floor(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "both be set or both be empty",
        ):
            GrayscaleCalibration(
                line=(
                    1,
                    2,
                    3,
                ),
            )

    def test_rejects_wrong_length(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "must contain exactly 3 values",
        ):
            GrayscaleCalibration(
                floor=(
                    1,
                    2,
                ),  # type: ignore[arg-type]
                line=(
                    1,
                    2,
                    3,
                ),
            )

    def test_from_dict_none_returns_default(
        self,
    ) -> None:
        self.assertEqual(
            GrayscaleCalibration.from_dict(None),
            GrayscaleCalibration(),
        )

    def test_from_dict(self) -> None:
        calibration = GrayscaleCalibration.from_dict(
            {
                "floor": [
                    100,
                    110,
                    120,
                ],
                "line": [
                    500,
                    510,
                    520,
                ],
            }
        )

        self.assertTrue(calibration.calibrated)
        self.assertEqual(
            calibration.floor,
            (
                100.0,
                110.0,
                120.0,
            ),
        )

    def test_from_dict_rejects_non_mapping(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "grayscale calibration must be an object",
        ):
            GrayscaleCalibration.from_dict(
                []  # type: ignore[arg-type]
            )


class RobotCalibrationTests(unittest.TestCase):
    def test_defaults(self) -> None:
        calibration = RobotCalibration.default()

        self.assertEqual(
            calibration.version,
            CALIBRATION_VERSION,
        )
        self.assertEqual(
            calibration.camera_mount,
            CameraMountCalibration(),
        )
        self.assertEqual(
            calibration.steering,
            SteeringCalibration(),
        )
        self.assertEqual(
            calibration.motors,
            MotorCalibration(),
        )
        self.assertEqual(
            calibration.grayscale,
            GrayscaleCalibration(),
        )

    def test_default_factories_create_distinct_objects(
        self,
    ) -> None:
        first = RobotCalibration()
        second = RobotCalibration()

        self.assertIsNot(
            first.camera_mount,
            second.camera_mount,
        )
        self.assertIsNot(
            first.steering,
            second.steering,
        )
        self.assertIsNot(
            first.motors,
            second.motors,
        )
        self.assertIsNot(
            first.grayscale,
            second.grayscale,
        )

    def test_accepts_integral_version_forms(
        self,
    ) -> None:
        for value in (
            CALIBRATION_VERSION,
            float(CALIBRATION_VERSION),
            str(CALIBRATION_VERSION),
        ):
            with self.subTest(value=value):
                calibration = RobotCalibration(
                    version=value  # type: ignore[arg-type]
                )

                self.assertEqual(
                    calibration.version,
                    CALIBRATION_VERSION,
                )

    def test_rejects_unsupported_version(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unsupported calibration version",
        ):
            RobotCalibration(version=CALIBRATION_VERSION + 1)

    def test_rejects_invalid_nested_types(
        self,
    ) -> None:
        cases = (
            (
                "camera_mount",
                CameraMountCalibration,
            ),
            (
                "steering",
                SteeringCalibration,
            ),
            (
                "motors",
                MotorCalibration,
            ),
            (
                "grayscale",
                GrayscaleCalibration,
            ),
        )

        for field_name, expected_type in cases:
            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    (f"{field_name} must be a {expected_type.__name__}"),
                ),
            ):
                kwargs: dict[str, object] = {
                    "camera_mount": (CameraMountCalibration()),
                    "steering": (SteeringCalibration()),
                    "motors": MotorCalibration(),
                    "grayscale": (GrayscaleCalibration()),
                }
                kwargs[field_name] = object()

                RobotCalibration(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_from_dict_empty_returns_defaults(
        self,
    ) -> None:
        self.assertEqual(
            RobotCalibration.from_dict({}),
            RobotCalibration.default(),
        )

    def test_from_dict(self) -> None:
        calibration = RobotCalibration.from_dict(
            {
                "version": CALIBRATION_VERSION,
                "camera_mount": {
                    "pan_offset": 2,
                    "tilt_offset": -3,
                },
                "steering": {
                    "offset": 4,
                },
                "motors": {
                    "left_trim": 0.8,
                    "right_trim": 0.9,
                },
                "grayscale": {
                    "floor": [
                        100,
                        110,
                        120,
                    ],
                    "line": [
                        500,
                        510,
                        520,
                    ],
                },
            }
        )

        self.assertEqual(
            calibration.camera_mount.pan_offset,
            2.0,
        )
        self.assertEqual(
            calibration.steering.offset,
            4.0,
        )
        self.assertEqual(
            calibration.motors.left_trim,
            0.8,
        )
        self.assertTrue(calibration.grayscale.calibrated)

    def test_from_dict_rejects_non_mapping(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "calibration data must be an object",
        ):
            RobotCalibration.from_dict(
                []  # type: ignore[arg-type]
            )

    def test_from_dict_rejects_invalid_nested_mapping(
        self,
    ) -> None:
        for field_name in (
            "camera_mount",
            "steering",
            "motors",
            "grayscale",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    "must be an object",
                ),
            ):
                RobotCalibration.from_dict(
                    {
                        field_name: [],
                    }
                )

    def test_to_dict(self) -> None:
        calibration = RobotCalibration(
            camera_mount=CameraMountCalibration(
                pan_offset=2,
                tilt_offset=-3,
            ),
            steering=SteeringCalibration(
                offset=4,
            ),
            motors=MotorCalibration(
                left_trim=0.8,
                right_trim=0.9,
            ),
            grayscale=GrayscaleCalibration(
                floor=(
                    100,
                    110,
                    120,
                ),
                line=(
                    500,
                    510,
                    520,
                ),
            ),
        )

        self.assertEqual(
            calibration.to_dict(),
            {
                "version": CALIBRATION_VERSION,
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
                    "floor": (
                        100.0,
                        110.0,
                        120.0,
                    ),
                    "line": (
                        500.0,
                        510.0,
                        520.0,
                    ),
                },
            },
        )

    def test_models_are_frozen(self) -> None:
        calibration = SteeringCalibration()

        with self.assertRaises(FrozenInstanceError):
            calibration.offset = 2.0  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
