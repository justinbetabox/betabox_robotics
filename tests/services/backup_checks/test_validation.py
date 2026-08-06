from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.backup_checks.validation import (
    validate_backup_name,
    validate_config,
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
        path = Path("/tmp/backup")

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
            "/tmp/backup",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/tmp/backup"),
        )

    def test_expands_user_directory(self) -> None:
        expanded = Path("/home/test/backups")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = validate_path(
                "~/backups",
                name="path",
            )

        self.assertEqual(
            result,
            expanded,
        )
        expanduser.assert_called_once_with()

    def test_preserves_relative_path(self) -> None:
        result = validate_path(
            "relative/backup",
            name="path",
        )

        self.assertEqual(
            result,
            Path("relative/backup"),
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
                    ("backup_root must be a string or Path"),
                ),
            ):
                validate_path(
                    value,
                    name="backup_root",
                )

    def test_error_uses_supplied_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("backup source must be a string or Path"),
        ):
            validate_path(
                None,
                name="backup source",
            )


class ValidateBackupNameTests(unittest.TestCase):
    def test_accepts_valid_names(self) -> None:
        for value in (
            "20260805-143500",
            "before-update",
            "classroom_1",
            "backup.v2",
            "Backup",
            "a",
            "1",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    validate_backup_name(value),
                    value,
                )

    def test_strips_surrounding_whitespace(
        self,
    ) -> None:
        self.assertEqual(
            validate_backup_name("  before-update  "),
            "before-update",
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
                    ("backup name must be a string"),
                ),
            ):
                validate_backup_name(value)

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
                    ("backup name cannot be empty"),
                ),
            ):
                validate_backup_name(value)

    def test_rejects_current_directory_name(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "backup name is invalid",
        ):
            validate_backup_name(".")

    def test_rejects_parent_directory_name(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "backup name is invalid",
        ):
            validate_backup_name("..")

    def test_rejects_path_traversal(self) -> None:
        for value in (
            "../outside",
            "backup/../outside",
            "..\\outside",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    (
                        "backup name may contain "
                        "only letters, numbers, "
                        "periods, underscores, "
                        "and hyphens"
                    ),
                ),
            ):
                validate_backup_name(value)

    def test_rejects_absolute_paths(self) -> None:
        for value in (
            "/tmp/backup",
            "\\backup",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    (
                        "backup name may contain "
                        "only letters, numbers, "
                        "periods, underscores, "
                        "and hyphens"
                    ),
                ),
            ):
                validate_backup_name(value)

    def test_rejects_whitespace_inside_name(
        self,
    ) -> None:
        for value in (
            "before update",
            "backup\tname",
            "backup\nname",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    (
                        "backup name may contain "
                        "only letters, numbers, "
                        "periods, underscores, "
                        "and hyphens"
                    ),
                ),
            ):
                validate_backup_name(value)

    def test_rejects_invalid_characters(self) -> None:
        for value in (
            "backup:name",
            "backup@home",
            "backup!",
            "backup#1",
            "backup$name",
            "backup(name)",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    (
                        "backup name may contain "
                        "only letters, numbers, "
                        "periods, underscores, "
                        "and hyphens"
                    ),
                ),
            ):
                validate_backup_name(value)

    def test_rejects_name_starting_with_period(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            (
                "backup name may contain only "
                "letters, numbers, periods, "
                "underscores, and hyphens"
            ),
        ):
            validate_backup_name(".hidden")

    def test_rejects_name_starting_with_hyphen(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            (
                "backup name may contain only "
                "letters, numbers, periods, "
                "underscores, and hyphens"
            ),
        ):
            validate_backup_name("-backup")

    def test_rejects_name_starting_with_underscore(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            (
                "backup name may contain only "
                "letters, numbers, periods, "
                "underscores, and hyphens"
            ),
        ):
            validate_backup_name("_backup")


if __name__ == "__main__":
    unittest.main()
