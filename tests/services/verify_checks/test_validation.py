from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.hardware_checks import (
    AudioStatus,
    BatteryStatus,
    I2CStatus,
    RobotHardwareStatus,
    SensorStatus,
    VisionStatus,
)
from betabox_robotics.services.verify_checks.models import (
    CheckResult,
)
from betabox_robotics.services.verify_checks.validation import (
    validate_checks,
    validate_command,
    validate_config,
    validate_hardware_status,
    validate_include_robot,
    validate_path,
    validate_string,
    validate_timeout,
)


def make_hardware_status() -> RobotHardwareStatus:
    return RobotHardwareStatus(
        i2c=I2CStatus(
            available=True,
            devices=[
                "0x14",
            ],
        ),
        passive_hardware_available=True,
        battery=BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        ),
        sensors=SensorStatus(
            grayscale_available=True,
            grayscale_values=[
                100,
                200,
                300,
            ],
            ultrasonic_configured=True,
        ),
        audio=AudioStatus(
            available=True,
            device="HifiBerry DAC",
        ),
        vision=VisionStatus(
            service_available=True,
            running=True,
            camera_running=True,
            camera_has_frame=True,
            clients=1,
        ),
    )


class ValidateConfigTests(unittest.TestCase):
    def test_accepts_platform_config(self) -> None:
        result = validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_rejects_invalid_config(self) -> None:
        for value in (
            None,
            object(),
            "config",
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "config must be a PlatformConfig",
                ),
            ):
                validate_config(value)


class ValidateStringTests(unittest.TestCase):
    def test_accepts_string(self) -> None:
        result = validate_string(
            "picamera2",
            name="module",
        )

        self.assertEqual(
            result,
            "picamera2",
        )

    def test_strips_surrounding_whitespace(
        self,
    ) -> None:
        result = validate_string(
            " picamera2 ",
            name="module",
        )

        self.assertEqual(
            result,
            "picamera2",
        )

    def test_rejects_non_string(self) -> None:
        for value in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "module must be a string",
                ),
            ):
                validate_string(
                    value,
                    name="module",
                )

    def test_rejects_empty_string(self) -> None:
        for value in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "module cannot be empty",
                ),
            ):
                validate_string(
                    value,
                    name="module",
                )

    def test_error_uses_supplied_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "speech backend must be a string",
        ):
            validate_string(
                None,
                name="speech backend",
            )


class ValidatePathTests(unittest.TestCase):
    def test_accepts_path(self) -> None:
        path = Path("/home/picar/media")

        result = validate_path(
            path,
            name="path",
        )

        self.assertEqual(
            result,
            path,
        )

    def test_accepts_string(self) -> None:
        result = validate_path(
            "/home/picar/media",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/home/picar/media"),
        )

    def test_expands_user_directory(self) -> None:
        expanded = Path("/home/picar/media")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = validate_path(
                "~/media",
                name="path",
            )

        self.assertEqual(
            result,
            expanded,
        )
        expanduser.assert_called_once_with()

    def test_preserves_relative_path(self) -> None:
        result = validate_path(
            "media/pictures",
            name="path",
        )

        self.assertEqual(
            result,
            Path("media/pictures"),
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
                    "path must be a string or Path",
                ),
            ):
                validate_path(
                    value,
                    name="path",
                )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            None,
            123,
            1.5,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("media_path must be a string or Path"),
                ),
            ):
                validate_path(
                    value,
                    name="media_path",
                )


class ValidateTimeoutTests(unittest.TestCase):
    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            validate_timeout(5),
            5,
        )

    def test_accepts_one(self) -> None:
        self.assertEqual(
            validate_timeout(1),
            1,
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
                    "timeout must be an integer",
                ),
            ):
                validate_timeout(value)

    def test_rejects_non_integer(self) -> None:
        for value in (
            None,
            1.5,
            "5",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "timeout must be an integer",
                ),
            ):
                validate_timeout(value)

    def test_rejects_non_positive_integer(self) -> None:
        for value in (
            0,
            -1,
            -10,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("timeout must be greater than 0"),
                ),
            ):
                validate_timeout(value)


class ValidateCommandTests(unittest.TestCase):
    def test_accepts_list(self) -> None:
        command = [
            "systemctl",
            "is-active",
            "betabox-launchpad.service",
        ]

        result = validate_command(command)

        self.assertEqual(
            result,
            command,
        )
        self.assertIsNot(
            result,
            command,
        )
        self.assertIsInstance(
            result,
            list,
        )

    def test_accepts_tuple(self) -> None:
        result = validate_command(
            (
                "configurable-http-proxy",
                "--version",
            )
        )

        self.assertEqual(
            result,
            [
                "configurable-http-proxy",
                "--version",
            ],
        )

    def test_strips_arguments(self) -> None:
        result = validate_command(
            [
                " systemctl ",
                " is-active ",
                " betabox-launchpad.service ",
            ]
        )

        self.assertEqual(
            result,
            [
                "systemctl",
                "is-active",
                "betabox-launchpad.service",
            ],
        )

    def test_rejects_string(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("command must be a sequence of strings"),
        ):
            validate_command("systemctl")

    def test_rejects_bytes(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("command must be a sequence of strings"),
        ):
            validate_command(b"systemctl")

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
                    ("command must be a sequence of strings"),
                ),
            ):
                validate_command(value)

    def test_rejects_non_string_argument(self) -> None:
        for value in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("command must contain only strings"),
                ),
            ):
                validate_command(
                    [
                        "command",
                        value,  # type: ignore[list-item]
                    ]
                )

    def test_rejects_empty_argument(self) -> None:
        for value in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("command cannot contain empty strings"),
                ),
            ):
                validate_command(
                    [
                        "command",
                        value,
                    ]
                )

    def test_rejects_empty_command(self) -> None:
        for value in (
            [],
            (),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "command cannot be empty",
                ),
            ):
                validate_command(value)


class ValidateIncludeRobotTests(unittest.TestCase):
    def test_accepts_true(self) -> None:
        self.assertTrue(validate_include_robot(True))

    def test_accepts_false(self) -> None:
        self.assertFalse(validate_include_robot(False))

    def test_rejects_non_boolean(self) -> None:
        for value in (
            None,
            0,
            1,
            "true",
            [],
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("include_robot must be a boolean"),
                ),
            ):
                validate_include_robot(value)


class ValidateHardwareStatusTests(unittest.TestCase):
    def test_accepts_hardware_status(self) -> None:
        hardware = make_hardware_status()

        result = validate_hardware_status(hardware)

        self.assertIs(
            result,
            hardware,
        )

    def test_rejects_invalid_hardware_status(
        self,
    ) -> None:
        for value in (
            None,
            object(),
            {},
            "hardware",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("hardware must be a RobotHardwareStatus"),
                ),
            ):
                validate_hardware_status(value)


class ValidateChecksTests(unittest.TestCase):
    def test_accepts_tuple(self) -> None:
        checks = (
            CheckResult(
                name="camera:picamera2",
                ok=True,
                message="import ok",
            ),
            CheckResult(
                name="vision:service",
                ok=False,
                message="Vision service degraded",
            ),
        )

        result = validate_checks(checks)

        self.assertIs(
            result,
            checks,
        )

    def test_accepts_empty_tuple(self) -> None:
        checks: tuple[CheckResult, ...] = ()

        result = validate_checks(checks)

        self.assertIs(
            result,
            checks,
        )

    def test_rejects_non_tuple(self) -> None:
        for value in (
            [],
            {},
            "checks",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "checks must be a tuple",
                ),
            ):
                validate_checks(value)

    def test_rejects_invalid_check_value(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("checks must contain only CheckResult values"),
        ):
            validate_checks(
                (
                    CheckResult(
                        name="camera:picamera2",
                        ok=True,
                    ),
                    object(),  # type: ignore[arg-type]
                )
            )


if __name__ == "__main__":
    unittest.main()
