from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.install_checks.models import (
    CheckResult,
)
from betabox_robotics.services.install_checks.validation import (
    validate_checks,
    validate_command,
    validate_config,
    validate_optional_string,
    validate_path,
    validate_string,
    validate_timeout,
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
        self.assertEqual(
            validate_string(
                "service-user",
                name="username",
            ),
            "service-user",
        )

    def test_strips_surrounding_whitespace(
        self,
    ) -> None:
        self.assertEqual(
            validate_string(
                " service-user ",
                name="username",
            ),
            "service-user",
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
                    "username must be a string",
                ),
            ):
                validate_string(
                    value,
                    name="username",
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
                    "username cannot be empty",
                ),
            ):
                validate_string(
                    value,
                    name="username",
                )

    def test_error_uses_supplied_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "module must be a string",
        ):
            validate_string(
                None,
                name="module",
            )


class ValidateOptionalStringTests(unittest.TestCase):
    def test_accepts_none(self) -> None:
        self.assertIsNone(
            validate_optional_string(
                None,
                name="requested_user",
            )
        )

    def test_accepts_and_strips_string(self) -> None:
        self.assertEqual(
            validate_optional_string(
                " picar ",
                name="requested_user",
            ),
            "picar",
        )

    def test_rejects_empty_string(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "requested_user cannot be empty",
        ):
            validate_optional_string(
                " ",
                name="requested_user",
            )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "requested_user must be a string",
                ),
            ):
                validate_optional_string(
                    value,
                    name="requested_user",
                )


class ValidatePathTests(unittest.TestCase):
    def test_accepts_path(self) -> None:
        path = Path("/tmp/install-check")

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
            "/tmp/install-check",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/tmp/install-check"),
        )

    def test_expands_user_directory(self) -> None:
        expanded = Path("/home/test/install-check")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = validate_path(
                "~/install-check",
                name="path",
            )

        self.assertEqual(
            result,
            expanded,
        )
        expanduser.assert_called_once_with()

    def test_preserves_relative_path(self) -> None:
        result = validate_path(
            "relative/path",
            name="path",
        )

        self.assertEqual(
            result,
            Path("relative/path"),
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
                    ("media_root must be a string or Path"),
                ),
            ):
                validate_path(
                    value,
                    name="media_root",
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
            "is-enabled",
            "jupyterhub.service",
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
                "betabox",
                "--help",
            )
        )

        self.assertEqual(
            result,
            [
                "betabox",
                "--help",
            ],
        )

    def test_strips_arguments(self) -> None:
        result = validate_command(
            [
                " systemctl ",
                " is-enabled ",
                " service.service ",
            ]
        )

        self.assertEqual(
            result,
            [
                "systemctl",
                "is-enabled",
                "service.service",
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


class ValidateChecksTests(unittest.TestCase):
    def test_accepts_tuple(self) -> None:
        checks = (
            CheckResult(
                name="check:one",
                ok=True,
            ),
            CheckResult(
                name="check:two",
                ok=False,
                message="failed",
            ),
        )

        result = validate_checks(checks)

        self.assertIs(
            result,
            checks,
        )

    def test_accepts_empty_tuple(self) -> None:
        checks: tuple[CheckResult, ...] = ()

        self.assertIs(
            validate_checks(checks),
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
                        name="check:one",
                        ok=True,
                    ),
                    object(),  # type: ignore[arg-type]
                )
            )


if __name__ == "__main__":
    unittest.main()
