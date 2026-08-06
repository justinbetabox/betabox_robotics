from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.system_checks.validation import (
    validate_config,
    validate_interface_name,
    validate_path,
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


class ValidatePathTests(unittest.TestCase):
    def test_accepts_path(self) -> None:
        path = Path("/tmp/system-health")

        result = validate_path(
            path,
            name="path",
        )

        self.assertEqual(
            result,
            path,
        )

    def test_returns_new_path_for_string(self) -> None:
        result = validate_path(
            "/tmp/system-health",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/tmp/system-health"),
        )
        self.assertIsInstance(
            result,
            Path,
        )

    def test_expands_user_directory(self) -> None:
        with patch.object(
            Path,
            "expanduser",
            return_value=Path("/home/test/system-health"),
        ) as expanduser:
            result = validate_path(
                "~/system-health",
                name="path",
            )

        self.assertEqual(
            result,
            Path("/home/test/system-health"),
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
                    "location must be a string or Path",
                ),
            ):
                validate_path(
                    value,
                    name="location",
                )

    def test_error_uses_supplied_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "disk_path must be a string or Path",
        ):
            validate_path(
                None,
                name="disk_path",
            )


class ValidateInterfaceNameTests(unittest.TestCase):
    def test_accepts_interface_name(self) -> None:
        self.assertEqual(
            validate_interface_name("wlan0"),
            "wlan0",
        )

    def test_strips_surrounding_whitespace(self) -> None:
        self.assertEqual(
            validate_interface_name(" eth0 "),
            "eth0",
        )

    def test_preserves_valid_internal_characters(
        self,
    ) -> None:
        for value in (
            "enp1s0",
            "wlan0",
            "eth0.10",
            "br-1234",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    validate_interface_name(value),
                    value,
                )

    def test_rejects_invalid_type(self) -> None:
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
                    "name must be a string",
                ),
            ):
                validate_interface_name(value)

    def test_rejects_empty_name(self) -> None:
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
                    "name cannot be empty",
                ),
            ):
                validate_interface_name(value)


if __name__ == "__main__":
    unittest.main()
