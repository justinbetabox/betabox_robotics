from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.restore import (
    _validate_dry_run,
    backup_path,
    list_backups,
    main,
    print_backups,
    print_report,
    restore_backup,
)
from betabox_robotics.services.restore_checks import (
    RestoreItem,
)

MODULE = "betabox_robotics.services.restore"


def make_restored_item() -> RestoreItem:
    return RestoreItem(
        source=("/backups/test-backup/home/student/file.txt"),
        destination="/home/student/file.txt",
        restored=True,
        message="restored",
    )


def make_dry_run_item() -> RestoreItem:
    return RestoreItem(
        source=("/backups/test-backup/home/student/file.txt"),
        destination="/home/student/file.txt",
        restored=False,
        message="dry run",
    )


def make_missing_item() -> RestoreItem:
    return RestoreItem(
        source=("/backups/test-backup/home/student/missing.txt"),
        destination="/home/student/missing.txt",
        restored=False,
        message="source missing in backup",
    )


class ValidateDryRunTests(unittest.TestCase):
    def test_accepts_true(self) -> None:
        self.assertTrue(_validate_dry_run(True))

    def test_accepts_false(self) -> None:
        self.assertFalse(_validate_dry_run(False))

    def test_rejects_non_boolean(self) -> None:
        for value in (
            None,
            0,
            1,
            "true",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "dry_run must be a boolean",
                ),
            ):
                _validate_dry_run(value)


class ListBackupsTests(unittest.TestCase):
    def test_delegates_to_backup_storage(self) -> None:
        backups = (
            Path("/backups/new"),
            Path("/backups/old"),
        )

        with patch(
            f"{MODULE}.list_backup_directories",
            return_value=backups,
        ) as list_directories:
            result = list_backups()

        self.assertIs(
            result,
            backups,
        )
        list_directories.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG.paths.backup_root
        )

    def test_rejects_invalid_config_before_listing(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.list_backup_directories") as list_directories,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            list_backups(
                object()  # type: ignore[arg-type]
            )

        list_directories.assert_not_called()

    def test_unexpected_storage_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.list_backup_directories",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            list_backups()

        self.assertIs(
            context.exception,
            error,
        )


class BackupPathTests(unittest.TestCase):
    def test_builds_backup_path(self) -> None:
        backup_root = Path("/backups")

        with patch(
            f"{MODULE}.validate_path",
            return_value=backup_root,
        ) as validate_path:
            result = backup_path("test-backup")

        self.assertEqual(
            result,
            backup_root / "test-backup",
        )
        validate_path.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG.paths.backup_root,
            name="backup_root",
        )

    def test_uses_validated_backup_name(self) -> None:
        with (
            patch(
                f"{MODULE}.validate_backup_name",
                return_value="clean-name",
            ) as validate_name,
            patch(
                f"{MODULE}.validate_path",
                return_value=Path("/backups"),
            ),
        ):
            result = backup_path(" raw-name ")

        validate_name.assert_called_once_with(" raw-name ")
        self.assertEqual(
            result,
            Path("/backups/clean-name"),
        )

    def test_rejects_invalid_config_before_name(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.validate_backup_name") as validate_name,
            patch(f"{MODULE}.validate_path") as validate_path,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            backup_path(
                "test-backup",
                object(),  # type: ignore[arg-type]
            )

        validate_name.assert_not_called()
        validate_path.assert_not_called()

    def test_rejects_invalid_name_before_root_path(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.validate_backup_name",
                side_effect=ValueError("backup name is invalid"),
            ),
            patch(f"{MODULE}.validate_path") as validate_path,
            self.assertRaisesRegex(
                ValueError,
                "backup name is invalid",
            ),
        ):
            backup_path("../invalid")

        validate_path.assert_not_called()


class RestoreBackupTests(unittest.TestCase):
    def test_restores_configured_paths(self) -> None:
        backup_dir = Path("/backups/test-backup")
        restore_paths = DEFAULT_PLATFORM_CONFIG.paths.restore_paths

        items = tuple(
            RestoreItem(
                source=str(backup_dir / Path(destination).as_posix().lstrip("/")),
                destination=str(destination),
                restored=True,
                message="restored",
            )
            for destination in restore_paths
        )

        with (
            patch(
                f"{MODULE}.backup_path",
                return_value=backup_dir,
            ) as get_backup_path,
            patch.object(
                Path,
                "exists",
                return_value=True,
            ) as exists,
            patch(
                f"{MODULE}.restore_item",
                side_effect=items,
            ) as restore_item,
        ):
            result = restore_backup("test-backup")

        self.assertEqual(
            result,
            items,
        )
        self.assertIsInstance(
            result,
            tuple,
        )

        get_backup_path.assert_called_once_with(
            "test-backup",
            DEFAULT_PLATFORM_CONFIG,
        )
        exists.assert_called_once_with()

        self.assertEqual(
            restore_item.call_args_list,
            [
                call(
                    backup_dir,
                    destination,
                    dry_run=False,
                )
                for destination in restore_paths
            ],
        )

    def test_passes_dry_run_to_each_item(self) -> None:
        backup_dir = Path("/backups/test-backup")
        restore_paths = DEFAULT_PLATFORM_CONFIG.paths.restore_paths

        with (
            patch(
                f"{MODULE}.backup_path",
                return_value=backup_dir,
            ),
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.restore_item",
                return_value=make_dry_run_item(),
            ) as restore_item,
        ):
            result = restore_backup(
                "test-backup",
                dry_run=True,
            )

        self.assertEqual(
            len(result),
            len(restore_paths),
        )
        self.assertEqual(
            restore_item.call_args_list,
            [
                call(
                    backup_dir,
                    destination,
                    dry_run=True,
                )
                for destination in restore_paths
            ],
        )

    def test_raises_when_backup_is_missing(
        self,
    ) -> None:
        backup_dir = Path("/backups/test-backup")

        with (
            patch(
                f"{MODULE}.backup_path",
                return_value=backup_dir,
            ),
            patch.object(
                Path,
                "exists",
                return_value=False,
            ),
            patch(f"{MODULE}.restore_item") as restore_item,
            self.assertRaisesRegex(
                FileNotFoundError,
                "Backup not found: test-backup",
            ),
        ):
            restore_backup("test-backup")

        restore_item.assert_not_called()

    def test_validates_config_before_dry_run(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}._validate_dry_run") as validate_dry_run,
            patch(f"{MODULE}.backup_path") as get_backup_path,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            restore_backup(
                "test-backup",
                config=object(),  # type: ignore[arg-type]
            )

        validate_dry_run.assert_not_called()
        get_backup_path.assert_not_called()

    def test_validates_dry_run_before_backup_path(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.backup_path") as get_backup_path,
            self.assertRaisesRegex(
                TypeError,
                "dry_run must be a boolean",
            ),
        ):
            restore_backup(
                "test-backup",
                dry_run=1,  # type: ignore[arg-type]
            )

        get_backup_path.assert_not_called()

    def test_backup_path_error_propagates(self) -> None:
        error = ValueError("backup name is invalid")

        with (
            patch(
                f"{MODULE}.backup_path",
                side_effect=error,
            ),
            self.assertRaises(ValueError) as context,
        ):
            restore_backup("../invalid")

        self.assertIs(
            context.exception,
            error,
        )

    def test_unexpected_restore_item_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.backup_path",
                return_value=Path("/backups/test-backup"),
            ),
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.restore_item",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            restore_backup("test-backup")

        self.assertIs(
            context.exception,
            error,
        )


class PrintBackupsTests(unittest.TestCase):
    def test_prints_backup_names(self) -> None:
        backups = (
            Path("/backups/new"),
            Path("/backups/old"),
        )

        with patch("builtins.print") as print_message:
            print_backups(backups)

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Backups"),
                call("==============="),
                call(),
                call("new"),
                call("old"),
                call(),
            ],
        )

    def test_prints_empty_message(self) -> None:
        with patch("builtins.print") as print_message:
            print_backups(())

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Backups"),
                call("==============="),
                call(),
                call("No backups found."),
                call(),
            ],
        )

    def test_rejects_non_tuple_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "backups must be a tuple",
            ),
        ):
            print_backups(
                []  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class PrintReportTests(unittest.TestCase):
    def test_prints_restore_report(self) -> None:
        items = (
            make_restored_item(),
            make_missing_item(),
        )

        with patch("builtins.print") as print_message:
            print_report(
                "test-backup",
                items,
                dry_run=False,
            )

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Restore"),
                call("==============="),
                call(),
                call("Backup: test-backup"),
                call("Mode:   restore"),
                call(),
                call("Items"),
                call("-----"),
                call(f"[RESTORED] {items[0].source}"),
                call(f"          -> {items[0].destination}"),
                call("          restored"),
                call(f"[SKIPPED] {items[1].source}"),
                call(f"          -> {items[1].destination}"),
                call("          source missing in backup"),
                call(),
            ],
        )

    def test_prints_dry_run_report(self) -> None:
        items = (
            make_dry_run_item(),
            make_missing_item(),
        )

        with patch("builtins.print") as print_message:
            print_report(
                "test-backup",
                items,
                dry_run=True,
            )

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Restore"),
                call("==============="),
                call(),
                call("Backup: test-backup"),
                call("Mode:   dry-run"),
                call(),
                call("Items"),
                call("-----"),
                call(f"[WOULD RESTORE] {items[0].source}"),
                call(f"          -> {items[0].destination}"),
                call("          dry run"),
                call(f"[SKIP] {items[1].source}"),
                call(f"          -> {items[1].destination}"),
                call("          source missing in backup"),
                call(),
            ],
        )

    def test_dry_run_does_not_query_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            patch("builtins.print"),
        ):
            print_report(
                "test-backup",
                (make_dry_run_item(),),
                dry_run=True,
            )

        exists.assert_not_called()

    def test_does_not_print_empty_item_message(
        self,
    ) -> None:
        item = RestoreItem(
            source="/source",
            destination="/destination",
            restored=True,
            message="",
        )

        with patch("builtins.print") as print_message:
            print_report(
                "test-backup",
                (item,),
                dry_run=False,
            )

        self.assertNotIn(
            call("          "),
            print_message.call_args_list,
        )

    def test_rejects_invalid_name_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaises(ValueError),
        ):
            print_report(
                "../invalid",
                (),
                dry_run=False,
            )

        print_message.assert_not_called()

    def test_rejects_invalid_dry_run_before_items(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "dry_run must be a boolean",
            ),
        ):
            print_report(
                "test-backup",
                [],  # type: ignore[arg-type]
                dry_run=1,  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_non_tuple_items(self) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "items must be a tuple",
            ),
        ):
            print_report(
                "test-backup",
                [],  # type: ignore[arg-type]
                dry_run=False,
            )

        print_message.assert_not_called()

    def test_rejects_invalid_item_values(self) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("items must contain only RestoreItem values"),
            ),
        ):
            print_report(
                "test-backup",
                (
                    object(),  # type: ignore[arg-type]
                ),
                dry_run=False,
            )

        print_message.assert_not_called()


class MainTests(unittest.TestCase):
    def test_list_mode_prints_backups(self) -> None:
        backups = (Path("/backups/test-backup"),)

        with (
            patch(
                f"{MODULE}.list_backups",
                return_value=backups,
            ) as list_backups_call,
            patch(f"{MODULE}.print_backups") as print_backups_call,
            patch(f"{MODULE}.restore_backup") as restore_backup_call,
        ):
            result = main(
                [
                    "--list",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        list_backups_call.assert_called_once_with()
        print_backups_call.assert_called_once_with(backups)
        restore_backup_call.assert_not_called()

    def test_missing_name_lists_backups(self) -> None:
        backups = (Path("/backups/test-backup"),)

        with (
            patch(
                f"{MODULE}.list_backups",
                return_value=backups,
            ) as list_backups_call,
            patch(f"{MODULE}.print_backups") as print_backups_call,
            patch(f"{MODULE}.restore_backup") as restore_backup_call,
        ):
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        list_backups_call.assert_called_once_with()
        print_backups_call.assert_called_once_with(backups)
        restore_backup_call.assert_not_called()

    def test_restore_mode_prints_report(self) -> None:
        items = (make_restored_item(),)

        with (
            patch(
                f"{MODULE}.restore_backup",
                return_value=items,
            ) as restore_backup_call,
            patch(f"{MODULE}.print_report") as print_report_call,
        ):
            result = main(
                [
                    "test-backup",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        restore_backup_call.assert_called_once_with(
            "test-backup",
            dry_run=False,
        )
        print_report_call.assert_called_once_with(
            "test-backup",
            items,
            dry_run=False,
        )

    def test_dry_run_mode_prints_report(self) -> None:
        items = (make_dry_run_item(),)

        with (
            patch(
                f"{MODULE}.restore_backup",
                return_value=items,
            ) as restore_backup_call,
            patch(f"{MODULE}.print_report") as print_report_call,
        ):
            result = main(
                [
                    "test-backup",
                    "--dry-run",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        restore_backup_call.assert_called_once_with(
            "test-backup",
            dry_run=True,
        )
        print_report_call.assert_called_once_with(
            "test-backup",
            items,
            dry_run=True,
        )

    def test_returns_one_for_missing_backup(self) -> None:
        with (
            patch(
                f"{MODULE}.restore_backup",
                side_effect=FileNotFoundError("Backup not found: missing"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(
                [
                    "missing",
                ]
            )

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("Backup not found: missing")

    def test_returns_one_for_validation_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.restore_backup",
                side_effect=ValueError("backup name is invalid"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(
                [
                    "../invalid",
                ]
            )

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("backup name is invalid")

    def test_returns_one_for_type_error(self) -> None:
        with (
            patch(
                f"{MODULE}.restore_backup",
                side_effect=TypeError("invalid type"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(
                [
                    "test-backup",
                ]
            )

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("invalid type")

    def test_returns_one_for_os_error(self) -> None:
        with (
            patch(
                f"{MODULE}.restore_backup",
                side_effect=OSError("permission denied"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(
                [
                    "test-backup",
                ]
            )

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with(
            "Unable to restore backup: permission denied"
        )

    def test_unexpected_error_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.restore_backup",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main(
                [
                    "test-backup",
                ]
            )

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
