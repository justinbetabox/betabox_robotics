from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.hardware import Pins
from betabox_robotics.robots.config import (
    AudioConfig,
    BatteryConfig,
    CameraMountConfig,
    DriveConfig,
    GrayscaleConfig,
    MotorConfig,
    RobotConfig,
    SensorsConfig,
    SteeringConfig,
    SystemConfig,
    UltrasonicConfig,
    VisionConfig,
    _validate_bool,
    _validate_number,
    _validate_positive_number,
    _validate_string,
)


def make_left_motor() -> MotorConfig:
    return MotorConfig(
        pwm=Pins.P13,
        direction=Pins.D4,
        reversed=True,
        trim=1.0,
    )


def make_right_motor() -> MotorConfig:
    return MotorConfig(
        pwm=Pins.P12,
        direction=Pins.D5,
        reversed=False,
        trim=1.0,
    )


def make_steering() -> SteeringConfig:
    return SteeringConfig(
        servo=Pins.P2,
        min_angle=-30,
        max_angle=30,
    )


def make_camera_mount() -> CameraMountConfig:
    return CameraMountConfig(
        pan_servo=Pins.P0,
        tilt_servo=Pins.P1,
    )


def make_drive() -> DriveConfig:
    return DriveConfig(
        left_motor=make_left_motor(),
        right_motor=make_right_motor(),
        steering=make_steering(),
    )


def make_ultrasonic() -> UltrasonicConfig:
    return UltrasonicConfig(
        trigger=Pins.D2,
        echo=Pins.D3,
    )


def make_grayscale() -> GrayscaleConfig:
    return GrayscaleConfig(
        left=Pins.A0,
        middle=Pins.A1,
        right=Pins.A2,
    )


def make_battery() -> BatteryConfig:
    return BatteryConfig(
        channel=Pins.A4,
    )


def make_sensors() -> SensorsConfig:
    return SensorsConfig(
        ultrasonic=make_ultrasonic(),
        grayscale=make_grayscale(),
        battery=make_battery(),
    )


def make_robot_config() -> RobotConfig:
    return RobotConfig(
        drive=make_drive(),
        camera_mount=make_camera_mount(),
        sensors=make_sensors(),
    )


class ValidationHelperTests(unittest.TestCase):
    def test_validate_number(self) -> None:
        self.assertEqual(
            _validate_number(
                5,
                name="value",
            ),
            5.0,
        )
        self.assertEqual(
            _validate_number(
                2.5,
                name="value",
            ),
            2.5,
        )

    def test_validate_number_rejects_invalid_types(self) -> None:
        for value in (
            True,
            False,
            "5",
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "value must be a number",
                ),
            ):
                _validate_number(
                    value,
                    name="value",
                )

    def test_validate_number_rejects_non_finite_values(self) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be finite",
                ),
            ):
                _validate_number(
                    value,
                    name="value",
                )

    def test_validate_positive_number(self) -> None:
        self.assertEqual(
            _validate_positive_number(
                2,
                name="value",
            ),
            2.0,
        )

    def test_validate_positive_number_rejects_non_positive(self) -> None:
        for value in (
            0,
            -1,
            -0.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be greater than zero",
                ),
            ):
                _validate_positive_number(
                    value,
                    name="value",
                )

    def test_validate_string_normalizes_value(self) -> None:
        self.assertEqual(
            _validate_string(
                " value ",
                name="field",
            ),
            "value",
        )

    def test_validate_string_allows_none_when_requested(self) -> None:
        self.assertIsNone(
            _validate_string(
                None,
                name="field",
                allow_none=True,
            )
        )

    def test_validate_string_rejects_invalid_values(self) -> None:
        for value in (
            1,
            object(),
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "field must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="field",
                )

        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "field cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="field",
                )

    def test_validate_bool(self) -> None:
        self.assertTrue(
            _validate_bool(
                True,
                name="value",
            )
        )
        self.assertFalse(
            _validate_bool(
                False,
                name="value",
            )
        )

    def test_validate_bool_rejects_non_boolean(self) -> None:
        for value in (
            0,
            1,
            "true",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "value must be a boolean",
                ),
            ):
                _validate_bool(
                    value,
                    name="value",
                )


class MotorConfigTests(unittest.TestCase):
    def test_create(self) -> None:
        config = make_left_motor()

        self.assertIs(
            config.pwm,
            Pins.P13,
        )
        self.assertIs(
            config.direction,
            Pins.D4,
        )
        self.assertTrue(config.reversed)
        self.assertEqual(
            config.trim,
            1.0,
        )

    def test_normalizes_trim(self) -> None:
        config = MotorConfig(
            pwm=Pins.P13,
            direction=Pins.D4,
            trim=1,
        )

        self.assertEqual(
            config.trim,
            1.0,
        )

    def test_accepts_trim_boundaries(self) -> None:
        for value in (
            0,
            1,
        ):
            with self.subTest(value=value):
                config = MotorConfig(
                    pwm=Pins.P13,
                    direction=Pins.D4,
                    trim=value,
                )

                self.assertEqual(
                    config.trim,
                    float(value),
                )

    def test_rejects_invalid_pwm(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "pwm must be a PWMChannel",
        ):
            MotorConfig(
                pwm=Pins.D0,  # type: ignore[arg-type]
                direction=Pins.D4,
            )

    def test_rejects_invalid_direction(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "direction must be a DigitalPin",
        ):
            MotorConfig(
                pwm=Pins.P13,
                direction=Pins.P0,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_reversed(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "reversed must be a boolean",
        ):
            MotorConfig(
                pwm=Pins.P13,
                direction=Pins.D4,
                reversed=1,  # type: ignore[arg-type]
            )

    def test_rejects_trim_outside_range(self) -> None:
        for value in (
            -0.1,
            1.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "trim must be between",
                ),
            ):
                MotorConfig(
                    pwm=Pins.P13,
                    direction=Pins.D4,
                    trim=value,
                )


class SteeringConfigTests(unittest.TestCase):
    def test_create(self) -> None:
        config = make_steering()

        self.assertIs(
            config.servo,
            Pins.P2,
        )
        self.assertEqual(
            config.min_angle,
            -30.0,
        )
        self.assertEqual(
            config.max_angle,
            30.0,
        )

    def test_rejects_invalid_servo(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "servo must be a PWMChannel",
        ):
            SteeringConfig(
                servo=Pins.D0,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_angle_order(self) -> None:
        for minimum, maximum in (
            (0, 0),
            (10, -10),
        ):
            with (
                self.subTest(
                    minimum=minimum,
                    maximum=maximum,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "min_angle must be less than max_angle",
                ),
            ):
                SteeringConfig(
                    servo=Pins.P2,
                    min_angle=minimum,
                    max_angle=maximum,
                )


class CameraMountConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = make_camera_mount()

        self.assertEqual(
            config.pan_min_angle,
            -45.0,
        )
        self.assertEqual(
            config.pan_max_angle,
            45.0,
        )
        self.assertEqual(
            config.tilt_min_angle,
            -30.0,
        )
        self.assertEqual(
            config.tilt_max_angle,
            45.0,
        )
        self.assertEqual(
            config.pan_center,
            0.0,
        )
        self.assertEqual(
            config.tilt_center,
            0.0,
        )
        self.assertFalse(config.pan_reversed)
        self.assertFalse(config.tilt_reversed)

    def test_rejects_invalid_servos(self) -> None:
        cases = (
            (
                "pan_servo",
                Pins.D0,
                "pan_servo must be a PWMChannel",
            ),
            (
                "tilt_servo",
                Pins.D1,
                "tilt_servo must be a PWMChannel",
            ),
        )

        for field_name, value, message in cases:
            kwargs: dict[str, object] = {
                "pan_servo": Pins.P0,
                "tilt_servo": Pins.P1,
            }
            kwargs[field_name] = value

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    message,
                ),
            ):
                CameraMountConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_rejects_invalid_angle_ranges(self) -> None:
        cases = (
            {
                "pan_min_angle": 10,
                "pan_max_angle": 10,
            },
            {
                "tilt_min_angle": 10,
                "tilt_max_angle": -10,
            },
        )

        for values in cases:
            kwargs: dict[str, object] = {
                "pan_servo": Pins.P0,
                "tilt_servo": Pins.P1,
            }
            kwargs.update(values)

            with (
                self.subTest(values=values),
                self.assertRaises(ValueError),
            ):
                CameraMountConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_rejects_centers_outside_ranges(self) -> None:
        cases = (
            {
                "pan_center": 46,
            },
            {
                "pan_center": -46,
            },
            {
                "tilt_center": 46,
            },
            {
                "tilt_center": -31,
            },
        )

        for values in cases:
            kwargs: dict[str, object] = {
                "pan_servo": Pins.P0,
                "tilt_servo": Pins.P1,
            }
            kwargs.update(values)

            with (
                self.subTest(values=values),
                self.assertRaises(ValueError),
            ):
                CameraMountConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_rejects_invalid_reversed_values(self) -> None:
        for field_name in (
            "pan_reversed",
            "tilt_reversed",
        ):
            kwargs: dict[str, object] = {
                "pan_servo": Pins.P0,
                "tilt_servo": Pins.P1,
            }
            kwargs[field_name] = 1

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    "must be a boolean",
                ),
            ):
                CameraMountConfig(
                    **kwargs  # type: ignore[arg-type]
                )


class DriveConfigTests(unittest.TestCase):
    def test_create(self) -> None:
        left = make_left_motor()
        right = make_right_motor()
        steering = make_steering()

        config = DriveConfig(
            left_motor=left,
            right_motor=right,
            steering=steering,
        )

        self.assertIs(
            config.left_motor,
            left,
        )
        self.assertIs(
            config.right_motor,
            right,
        )
        self.assertIs(
            config.steering,
            steering,
        )

    def test_rejects_invalid_nested_configs(self) -> None:
        cases = (
            (
                "left_motor",
                "left_motor must be a MotorConfig",
            ),
            (
                "right_motor",
                "right_motor must be a MotorConfig",
            ),
            (
                "steering",
                "steering must be a SteeringConfig",
            ),
        )

        for field_name, message in cases:
            kwargs: dict[str, object] = {
                "left_motor": make_left_motor(),
                "right_motor": make_right_motor(),
                "steering": make_steering(),
            }
            kwargs[field_name] = object()

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    message,
                ),
            ):
                DriveConfig(
                    **kwargs  # type: ignore[arg-type]
                )


class UltrasonicConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = make_ultrasonic()

        self.assertEqual(
            config.timeout,
            0.02,
        )

    def test_rejects_invalid_pins(self) -> None:
        cases = (
            (
                "trigger",
                Pins.P0,
                "trigger must be a DigitalPin",
            ),
            (
                "echo",
                Pins.P1,
                "echo must be a DigitalPin",
            ),
        )

        for field_name, value, message in cases:
            kwargs: dict[str, object] = {
                "trigger": Pins.D2,
                "echo": Pins.D3,
            }
            kwargs[field_name] = value

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    message,
                ),
            ):
                UltrasonicConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_rejects_non_positive_timeout(self) -> None:
        for value in (
            0,
            -0.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "timeout must be greater than zero",
                ),
            ):
                UltrasonicConfig(
                    trigger=Pins.D2,
                    echo=Pins.D3,
                    timeout=value,
                )


class GrayscaleConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = make_grayscale()

        self.assertEqual(
            config.reference,
            (
                1000,
                1000,
                1000,
            ),
        )

    def test_rejects_invalid_channels(self) -> None:
        for field_name in (
            "left",
            "middle",
            "right",
        ):
            kwargs: dict[str, object] = {
                "left": Pins.A0,
                "middle": Pins.A1,
                "right": Pins.A2,
            }
            kwargs[field_name] = Pins.D0

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    f"{field_name} must be an AnalogChannel",
                ),
            ):
                GrayscaleConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_rejects_non_tuple_reference(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "reference must be a tuple",
        ):
            GrayscaleConfig(
                left=Pins.A0,
                middle=Pins.A1,
                right=Pins.A2,
                reference=[  # type: ignore[arg-type]
                    1000,
                    1000,
                    1000,
                ],
            )

    def test_rejects_wrong_reference_length(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "reference must contain exactly 3 values",
        ):
            GrayscaleConfig(
                left=Pins.A0,
                middle=Pins.A1,
                right=Pins.A2,
                reference=(1000, 1000),  # type: ignore[arg-type]
            )

    def test_rejects_invalid_reference_values(self) -> None:
        cases = (
            (
                (True, 1000, 1000),
                TypeError,
            ),
            (
                (1.5, 1000, 1000),
                TypeError,
            ),
            (
                (-1, 1000, 1000),
                ValueError,
            ),
        )

        for reference, exception_type in cases:
            with (
                self.subTest(reference=reference),
                self.assertRaises(exception_type),
            ):
                GrayscaleConfig(
                    left=Pins.A0,
                    middle=Pins.A1,
                    right=Pins.A2,
                    reference=reference,  # type: ignore[arg-type]
                )


class BatteryConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = make_battery()

        self.assertEqual(
            config.scale,
            3.0,
        )
        self.assertEqual(
            config.low_voltage,
            6.6,
        )
        self.assertEqual(
            config.critical_voltage,
            6.2,
        )

    def test_rejects_invalid_channel(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "channel must be an AnalogChannel",
        ):
            BatteryConfig(
                channel=Pins.D0,  # type: ignore[arg-type]
            )

    def test_rejects_non_positive_values(self) -> None:
        for field_name in (
            "scale",
            "low_voltage",
            "critical_voltage",
        ):
            kwargs: dict[str, object] = {
                "channel": Pins.A4,
                "scale": 3.0,
                "low_voltage": 6.6,
                "critical_voltage": 6.2,
            }
            kwargs[field_name] = 0

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    ValueError,
                    "must be greater than zero",
                ),
            ):
                BatteryConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_rejects_invalid_threshold_order(self) -> None:
        for critical in (
            6.6,
            7.0,
        ):
            with (
                self.subTest(critical=critical),
                self.assertRaisesRegex(
                    ValueError,
                    "critical_voltage must be less than low_voltage",
                ),
            ):
                BatteryConfig(
                    channel=Pins.A4,
                    low_voltage=6.6,
                    critical_voltage=critical,
                )


class SensorsConfigTests(unittest.TestCase):
    def test_create(self) -> None:
        ultrasonic = make_ultrasonic()
        grayscale = make_grayscale()
        battery = make_battery()

        config = SensorsConfig(
            ultrasonic=ultrasonic,
            grayscale=grayscale,
            battery=battery,
        )

        self.assertIs(
            config.ultrasonic,
            ultrasonic,
        )
        self.assertIs(
            config.grayscale,
            grayscale,
        )
        self.assertIs(
            config.battery,
            battery,
        )

    def test_rejects_invalid_nested_configs(self) -> None:
        cases = (
            (
                "ultrasonic",
                "ultrasonic must be an UltrasonicConfig",
            ),
            (
                "grayscale",
                "grayscale must be a GrayscaleConfig",
            ),
            (
                "battery",
                "battery must be a BatteryConfig",
            ),
        )

        for field_name, message in cases:
            kwargs: dict[str, object] = {
                "ultrasonic": make_ultrasonic(),
                "grayscale": make_grayscale(),
                "battery": make_battery(),
            }
            kwargs[field_name] = object()

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    message,
                ),
            ):
                SensorsConfig(
                    **kwargs  # type: ignore[arg-type]
                )


class VisionConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = VisionConfig()

        self.assertEqual(
            config.service_url,
            "http://127.0.0.1:8080",
        )
        self.assertEqual(
            config.request_timeout,
            10.0,
        )

    def test_normalizes_values(self) -> None:
        config = VisionConfig(
            service_url=" http://robot:8080 ",
            request_timeout=5,
        )

        self.assertEqual(
            config.service_url,
            "http://robot:8080",
        )
        self.assertEqual(
            config.request_timeout,
            5.0,
        )

    def test_rejects_invalid_url(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "service_url cannot be empty",
                ),
            ):
                VisionConfig(service_url=value)

    def test_rejects_non_positive_timeout(self) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "request_timeout must be greater than zero",
                ),
            ):
                VisionConfig(request_timeout=value)


class AudioConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = AudioConfig()

        self.assertEqual(
            config.speech_engine,
            "auto",
        )
        self.assertEqual(
            config.sample_rate,
            44100,
        )
        self.assertTrue(config.auto_amp)
        self.assertFalse(config.keep_amp_enabled)
        self.assertEqual(
            config.speech_volume,
            1.0,
        )

    def test_normalizes_strings(self) -> None:
        config = AudioConfig(
            speech_engine=" auto ",
            speech_language=" en-US ",
            piper_model=" model.onnx ",
            piper_voice=" voice ",
            preferred_output_device=" device ",
        )

        self.assertEqual(
            config.speech_engine,
            "auto",
        )
        self.assertEqual(
            config.speech_language,
            "en-US",
        )
        self.assertEqual(
            config.piper_model,
            "model.onnx",
        )
        self.assertEqual(
            config.piper_voice,
            "voice",
        )
        self.assertEqual(
            config.preferred_output_device,
            "device",
        )

    def test_allows_none_piper_model(self) -> None:
        self.assertIsNone(AudioConfig(piper_model=None).piper_model)

    def test_rejects_invalid_required_strings(self) -> None:
        fields = (
            "speech_engine",
            "speech_language",
            "piper_voice",
            "preferred_output_device",
        )

        for field_name in fields:
            kwargs: dict[str, object] = {
                field_name: " ",
            }

            with (
                self.subTest(field=field_name),
                self.assertRaises(ValueError),
            ):
                AudioConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_rejects_invalid_sample_rate(self) -> None:
        for value, exception_type in (
            (True, TypeError),
            (44100.0, TypeError),
            (0, ValueError),
            (-1, ValueError),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(exception_type),
            ):
                AudioConfig(
                    sample_rate=value  # type: ignore[arg-type]
                )

    def test_rejects_invalid_boolean_values(self) -> None:
        for field_name in (
            "auto_amp",
            "keep_amp_enabled",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    "must be a boolean",
                ),
            ):
                AudioConfig(
                    **{
                        field_name: 1,
                    }  # type: ignore[arg-type]
                )

    def test_accepts_volume_boundaries(self) -> None:
        for value in (
            0,
            1,
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    AudioConfig(speech_volume=value).speech_volume,
                    float(value),
                )

    def test_rejects_volume_outside_range(self) -> None:
        for value in (
            -0.1,
            1.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "speech_volume must be between",
                ),
            ):
                AudioConfig(speech_volume=value)


class SystemConfigTests(unittest.TestCase):
    def test_none_media_root(self) -> None:
        self.assertIsNone(SystemConfig().media_root)

    def test_accepts_path(self) -> None:
        path = Path("/home/picar/media")

        self.assertEqual(
            SystemConfig(media_root=path).media_root,
            path,
        )

    def test_accepts_and_expands_string(self) -> None:
        with patch(
            "betabox_robotics.robots.config.Path.expanduser",
            return_value=Path("/home/picar/media"),
        ):
            config = SystemConfig(media_root="~/media")

        self.assertEqual(
            config.media_root,
            Path("/home/picar/media"),
        )

    def test_rejects_invalid_media_root(self) -> None:
        for value in (
            True,
            123,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "media_root must be a string, Path, or None",
                ),
            ):
                SystemConfig(
                    media_root=value  # type: ignore[arg-type]
                )


class RobotConfigTests(unittest.TestCase):
    def test_create_with_defaults(self) -> None:
        config = make_robot_config()

        self.assertIsInstance(
            config.vision,
            VisionConfig,
        )
        self.assertIsInstance(
            config.audio,
            AudioConfig,
        )
        self.assertIsInstance(
            config.system,
            SystemConfig,
        )

    def test_default_factories_create_distinct_objects(self) -> None:
        first = make_robot_config()
        second = make_robot_config()

        self.assertIsNot(
            first.vision,
            second.vision,
        )
        self.assertIsNot(
            first.audio,
            second.audio,
        )
        self.assertIsNot(
            first.system,
            second.system,
        )

    def test_rejects_invalid_nested_configs(self) -> None:
        cases = (
            (
                "drive",
                "drive must be a DriveConfig",
            ),
            (
                "camera_mount",
                "camera_mount must be a CameraMountConfig",
            ),
            (
                "sensors",
                "sensors must be a SensorsConfig",
            ),
            (
                "vision",
                "vision must be a VisionConfig",
            ),
            (
                "audio",
                "audio must be an AudioConfig",
            ),
            (
                "system",
                "system must be a SystemConfig",
            ),
        )

        for field_name, message in cases:
            kwargs: dict[str, object] = {
                "drive": make_drive(),
                "camera_mount": make_camera_mount(),
                "sensors": make_sensors(),
                "vision": VisionConfig(),
                "audio": AudioConfig(),
                "system": SystemConfig(),
            }
            kwargs[field_name] = object()

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    message,
                ),
            ):
                RobotConfig(
                    **kwargs  # type: ignore[arg-type]
                )

    def test_configs_are_frozen(self) -> None:
        config = make_robot_config()

        with self.assertRaises(FrozenInstanceError):
            config.drive = make_drive()  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
