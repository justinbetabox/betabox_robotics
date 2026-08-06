from __future__ import annotations

import argparse
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.reset import (
    ResetItem,
    _validate_config,
    _validate_flag,
    _validate_items,
    _validate_path,
    main,
    parse_args,
    print_report,
    recreate_path,
    remove_path,
    run_reset,
)

MODULE = "betabox_robotics.services.reset"


def make_item(
    *,
    path: str = "/home/student/media",
    action: str = "removed",
    ok: bool = True,
    message: str = "",
) -> ResetItem:
    return ResetItem(
        path=path,
        action=action,
        ok=ok,
        message=message,
    )


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_platform_config(
        self,
    ) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_validate_config_rejects_invalid_value(
        self,
    ) -> None:
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
                    ("config must be a PlatformConfig"),
                ),
            ):
                _validate_config(value)

    def test_validate_path_accepts_path(
        self,
    ) -> None:
        path = Path("/home/student/media")

        result = _validate_path(
            path,
            name="path",
        )

        self.assertEqual(
            result,
            path,
        )

    def test_validate_path_accepts_string(
        self,
    ) -> None:
        result = _validate_path(
            "/home/student/media",
            name="path",
        )

        self.assertEqual(
            result,
            Path("/home/student/media"),
        )

    def test_validate_path_expands_user(
        self,
    ) -> None:
        expanded = Path("/home/student/media")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = _validate_path(
                "~/media",
                name="path",
            )

        expanduser.assert_called_once_with()
        self.assertEqual(
            result,
            expanded,
        )

    def test_validate_path_rejects_boolean(
        self,
    ) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("path must be a string or Path"),
                ),
            ):
                _validate_path(
                    value,
                    name="path",
                )

    def test_validate_path_rejects_invalid_type(
        self,
    ) -> None:
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
                    ("reset_path must be a string or Path"),
                ),
            ):
                _validate_path(
                    value,
                    name="reset_path",
                )

    def test_validate_flag_accepts_boolean(
        self,
    ) -> None:
        self.assertTrue(
            _validate_flag(
                True,
                name="dry_run",
            )
        )
        self.assertFalse(
            _validate_flag(
                False,
                name="dry_run",
            )
        )

    def test_validate_flag_rejects_non_boolean(
        self,
    ) -> None:
        for value in (
            None,
            0,
            1,
            "yes",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("dry_run must be a boolean"),
                ),
            ):
                _validate_flag(
                    value,
                    name="dry_run",
                )

    def test_validate_items_accepts_tuple(
        self,
    ) -> None:
        items = (make_item(),)

        result = _validate_items(items)

        self.assertIs(
            result,
            items,
        )

    def test_validate_items_accepts_empty_tuple(
        self,
    ) -> None:
        items: tuple[ResetItem, ...] = ()

        result = _validate_items(items)

        self.assertIs(
            result,
            items,
        )

    def test_validate_items_rejects_non_tuple(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "items must be a tuple",
        ):
            _validate_items(
                []  # type: ignore[arg-type]
            )

    def test_validate_items_rejects_invalid_item(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("items must contain only ResetItem values"),
        ):
            _validate_items(
                (
                    object(),  # type: ignore[arg-type]
                )
            )


class ResetItemTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        item = make_item()

        self.assertEqual(
            item.path,
            "/home/student/media",
        )
        self.assertEqual(
            item.action,
            "removed",
        )
        self.assertTrue(item.ok)
        self.assertEqual(
            item.message,
            "",
        )

    def test_strips_string_values(self) -> None:
        item = make_item(
            path=" /home/student/media ",
            action=" removed ",
            message=" complete ",
        )

        self.assertEqual(
            item.path,
            "/home/student/media",
        )
        self.assertEqual(
            item.action,
            "removed",
        )
        self.assertEqual(
            item.message,
            "complete",
        )

    def test_accepts_path_object(self) -> None:
        item = ResetItem(
            path=Path(  # type: ignore[arg-type]
                "/home/student/media"
            ),
            action="removed",
            ok=True,
        )

        self.assertEqual(
            item.path,
            "/home/student/media",
        )

    def test_allows_empty_message(self) -> None:
        item = make_item(message=" ")

        self.assertEqual(
            item.message,
            "",
        )

    def test_rejects_invalid_path(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("path must be a string or Path"),
        ):
            make_item(
                path=True,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_action(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "action must be a string",
        ):
            make_item(
                action=None,  # type: ignore[arg-type]
            )

    def test_rejects_empty_action(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "action cannot be empty",
        ):
            make_item(action=" ")

    def test_rejects_invalid_message(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "message must be a string",
        ):
            make_item(
                message=None,  # type: ignore[arg-type]
            )

    def test_rejects_non_boolean_ok(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "ok must be a boolean",
        ):
            make_item(
                ok=1,  # type: ignore[arg-type]
            )

    def test_is_frozen(self) -> None:
        item = make_item()

        with self.assertRaises(FrozenInstanceError):
            item.ok = False  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        item = make_item()

        self.assertFalse(
            hasattr(
                item,
                "__dict__",
            )
        )


class RemovePathTests(unittest.TestCase):
    def test_skips_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing"

            result = remove_path(
                path,
                dry_run=False,
            )

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="skip",
                ok=True,
                message="missing",
            ),
        )

    def test_dry_run_does_not_remove_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "media"
            path.mkdir()

            result = remove_path(
                path,
                dry_run=True,
            )

            self.assertTrue(path.exists())

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="would remove",
                ok=True,
                message="dry run",
            ),
        )

    def test_removes_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "media"
            path.mkdir()
            child = path / "file.txt"
            child.write_text(
                "content",
                encoding="utf-8",
            )

            result = remove_path(
                path,
                dry_run=False,
            )

            self.assertFalse(path.exists())

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="removed",
                ok=True,
            ),
        )

    def test_removes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "file.txt"
            path.write_text(
                "content",
                encoding="utf-8",
            )

            result = remove_path(
                path,
                dry_run=False,
            )

            self.assertFalse(path.exists())

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="removed",
                ok=True,
            ),
        )

    def test_reports_exists_error(self) -> None:
        path = Path("/home/student/media")

        with patch.object(
            Path,
            "exists",
            side_effect=OSError("permission denied"),
        ):
            result = remove_path(
                path,
                dry_run=False,
            )

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="remove failed",
                ok=False,
                message="permission denied",
            ),
        )

    def test_reports_directory_removal_error(
        self,
    ) -> None:
        path = Path("/home/student/media")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=True,
            ),
            patch(
                f"{MODULE}.shutil.rmtree",
                side_effect=OSError("remove failed"),
            ),
        ):
            result = remove_path(
                path,
                dry_run=False,
            )

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="remove failed",
                ok=False,
                message="remove failed",
            ),
        )

    def test_reports_file_removal_error(
        self,
    ) -> None:
        path = Path("/home/student/file.txt")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=False,
            ),
            patch.object(
                Path,
                "unlink",
                side_effect=OSError("unlink failed"),
            ),
        ):
            result = remove_path(
                path,
                dry_run=False,
            )

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="remove failed",
                ok=False,
                message="unlink failed",
            ),
        )

    def test_rejects_invalid_path_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("path must be a string or Path"),
            ),
        ):
            remove_path(
                True,  # type: ignore[arg-type]
                dry_run=False,
            )

        exists.assert_not_called()

    def test_rejects_invalid_dry_run_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("dry_run must be a boolean"),
            ),
        ):
            remove_path(
                "/home/student/media",
                dry_run=1,  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_unexpected_filesystem_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "exists",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            remove_path(
                "/home/student/media",
                dry_run=False,
            )

        self.assertIs(
            context.exception,
            error,
        )


class RecreatePathTests(unittest.TestCase):
    def test_dry_run_does_not_create_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "media"

            result = recreate_path(
                path,
                dry_run=True,
            )

            self.assertFalse(path.exists())

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="would recreate",
                ok=True,
                message="dry run",
            ),
        )

    def test_creates_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "parent" / "media"

            result = recreate_path(
                path,
                dry_run=False,
            )

            self.assertTrue(path.is_dir())

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="recreated",
                ok=True,
            ),
        )

    def test_existing_directory_succeeds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "media"
            path.mkdir()

            result = recreate_path(
                path,
                dry_run=False,
            )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.action,
            "recreated",
        )

    def test_uses_expected_mkdir_options(
        self,
    ) -> None:
        path = Path("/home/student/media")

        with patch.object(Path, "mkdir") as mkdir:
            result = recreate_path(
                path,
                dry_run=False,
            )

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        self.assertTrue(result.ok)

    def test_reports_creation_error(self) -> None:
        path = Path("/home/student/media")

        with patch.object(
            Path,
            "mkdir",
            side_effect=OSError("permission denied"),
        ):
            result = recreate_path(
                path,
                dry_run=False,
            )

        self.assertEqual(
            result,
            ResetItem(
                path=str(path),
                action="recreate failed",
                ok=False,
                message="permission denied",
            ),
        )

    def test_rejects_invalid_path_before_mkdir(
        self,
    ) -> None:
        with (
            patch.object(Path, "mkdir") as mkdir,
            self.assertRaisesRegex(
                TypeError,
                ("path must be a string or Path"),
            ),
        ):
            recreate_path(
                True,  # type: ignore[arg-type]
                dry_run=False,
            )

        mkdir.assert_not_called()

    def test_rejects_invalid_dry_run_before_mkdir(
        self,
    ) -> None:
        with (
            patch.object(Path, "mkdir") as mkdir,
            self.assertRaisesRegex(
                TypeError,
                ("dry_run must be a boolean"),
            ),
        ):
            recreate_path(
                "/home/student/media",
                dry_run=1,  # type: ignore[arg-type]
            )

        mkdir.assert_not_called()

    def test_unexpected_creation_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "mkdir",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            recreate_path(
                "/home/student/media",
                dry_run=False,
            )

        self.assertIs(
            context.exception,
            error,
        )


class RunResetTests(unittest.TestCase):
    def test_creates_backup_then_processes_paths(
        self,
    ) -> None:
        reset_paths = DEFAULT_PLATFORM_CONFIG.paths.reset_paths
        recreate_paths = DEFAULT_PLATFORM_CONFIG.paths.recreate_paths
        remove_results = tuple(
            ResetItem(
                path=str(path),
                action="removed",
                ok=True,
            )
            for path in reset_paths
        )
        recreate_results = tuple(
            ResetItem(
                path=str(path),
                action="recreated",
                ok=True,
            )
            for path in recreate_paths
        )
        report = SimpleNamespace(name="20260805-172100")

        with (
            patch(
                f"{MODULE}.create_backup",
                return_value=report,
            ) as create_backup,
            patch(
                f"{MODULE}.remove_path",
                side_effect=remove_results,
            ) as remove,
            patch(
                f"{MODULE}.recreate_path",
                side_effect=recreate_results,
            ) as recreate,
        ):
            backup_name, items = run_reset(
                dry_run=False,
                backup=True,
                config=DEFAULT_PLATFORM_CONFIG,
            )

        self.assertEqual(
            backup_name,
            "20260805-172100",
        )
        self.assertEqual(
            items,
            (
                *remove_results,
                *recreate_results,
            ),
        )
        self.assertIsInstance(
            items,
            tuple,
        )
        create_backup.assert_called_once_with(
            name=None,
            config=DEFAULT_PLATFORM_CONFIG,
        )
        self.assertEqual(
            remove.call_args_list,
            [
                call(
                    path,
                    dry_run=False,
                )
                for path in reset_paths
            ],
        )
        self.assertEqual(
            recreate.call_args_list,
            [
                call(
                    path,
                    dry_run=False,
                )
                for path in recreate_paths
            ],
        )

    def test_dry_run_does_not_create_backup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.create_backup") as create_backup,
            patch(
                f"{MODULE}.remove_path",
                return_value=make_item(
                    action="would remove",
                    message="dry run",
                ),
            ),
            patch(
                f"{MODULE}.recreate_path",
                return_value=make_item(
                    action="would recreate",
                    message="dry run",
                ),
            ),
        ):
            backup_name, _ = run_reset(
                dry_run=True,
                backup=True,
            )

        self.assertIsNone(backup_name)
        create_backup.assert_not_called()

    def test_skips_backup_when_disabled(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.create_backup") as create_backup,
            patch(
                f"{MODULE}.remove_path",
                return_value=make_item(),
            ),
            patch(
                f"{MODULE}.recreate_path",
                return_value=make_item(action="recreated"),
            ),
        ):
            backup_name, _ = run_reset(
                dry_run=False,
                backup=False,
            )

        self.assertIsNone(backup_name)
        create_backup.assert_not_called()

    def test_rejects_invalid_dry_run_before_backup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.create_backup") as create_backup,
            self.assertRaisesRegex(
                TypeError,
                ("dry_run must be a boolean"),
            ),
        ):
            run_reset(
                dry_run=1,  # type: ignore[arg-type]
                backup=True,
            )

        create_backup.assert_not_called()

    def test_rejects_invalid_backup_before_backup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.create_backup") as create_backup,
            self.assertRaisesRegex(
                TypeError,
                ("backup must be a boolean"),
            ),
        ):
            run_reset(
                dry_run=False,
                backup=1,  # type: ignore[arg-type]
            )

        create_backup.assert_not_called()

    def test_rejects_invalid_config_before_backup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.create_backup") as create_backup,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            run_reset(
                dry_run=False,
                backup=True,
                config=object(),  # type: ignore[arg-type]
            )

        create_backup.assert_not_called()

    def test_backup_error_propagates(self) -> None:
        error = OSError("backup failed")

        with (
            patch(
                f"{MODULE}.create_backup",
                side_effect=error,
            ),
            patch(f"{MODULE}.remove_path") as remove,
            self.assertRaises(OSError) as context,
        ):
            run_reset(
                dry_run=False,
                backup=True,
            )

        self.assertIs(
            context.exception,
            error,
        )
        remove.assert_not_called()

    def test_remove_error_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.create_backup",
                return_value=SimpleNamespace(name="backup"),
            ),
            patch(
                f"{MODULE}.remove_path",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            run_reset(
                dry_run=False,
                backup=True,
            )

        self.assertIs(
            context.exception,
            error,
        )


class PrintReportTests(unittest.TestCase):
    def test_prints_successful_reset_with_backup(
        self,
    ) -> None:
        items = (
            make_item(),
            make_item(
                path="/home/student/media",
                action="recreated",
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_report(
                dry_run=False,
                backup=True,
                backup_name="backup-001",
                items=items,
            )

        self.assertTrue(result)
        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Reset"),
                call("============="),
                call(),
                call("Mode:   reset"),
                call("Backup: backup-001"),
                call(),
                call("Items"),
                call("-----"),
                call("[OK] removed: /home/student/media"),
                call("[OK] recreated: /home/student/media"),
                call(),
                call("Reset completed successfully."),
                call(),
            ],
        )

    def test_prints_successful_dry_run_with_backup(
        self,
    ) -> None:
        items = (
            make_item(
                action="would remove",
                message="dry run",
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_report(
                dry_run=True,
                backup=True,
                backup_name=None,
                items=items,
            )

        self.assertTrue(result)
        self.assertIn(
            call("Backup: would create backup before reset"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Dry run completed successfully."),
            print_message.call_args_list,
        )

    def test_dry_run_without_backup_reports_skipped(
        self,
    ) -> None:
        with patch("builtins.print") as print_message:
            result = print_report(
                dry_run=True,
                backup=False,
                backup_name=None,
                items=(),
            )

        self.assertTrue(result)
        self.assertIn(
            call("Backup: skipped"),
            print_message.call_args_list,
        )

    def test_real_reset_without_backup_reports_skipped(
        self,
    ) -> None:
        with patch("builtins.print") as print_message:
            result = print_report(
                dry_run=False,
                backup=False,
                backup_name=None,
                items=(),
            )

        self.assertTrue(result)
        self.assertIn(
            call("Backup: skipped"),
            print_message.call_args_list,
        )

    def test_prints_failed_item(self) -> None:
        items = (
            make_item(
                action="remove failed",
                ok=False,
                message="permission denied",
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_report(
                dry_run=False,
                backup=False,
                backup_name=None,
                items=items,
            )

        self.assertFalse(result)
        self.assertIn(
            call("[FAIL] remove failed: /home/student/media"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("     permission denied"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Reset completed with errors."),
            print_message.call_args_list,
        )

    def test_rejects_invalid_dry_run_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("dry_run must be a boolean"),
            ),
        ):
            print_report(
                dry_run=1,  # type: ignore[arg-type]
                backup=True,
                backup_name=None,
                items=(),
            )

        print_message.assert_not_called()

    def test_rejects_invalid_backup_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("backup must be a boolean"),
            ),
        ):
            print_report(
                dry_run=False,
                backup=1,  # type: ignore[arg-type]
                backup_name=None,
                items=(),
            )

        print_message.assert_not_called()

    def test_rejects_invalid_items_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "items must be a tuple",
            ),
        ):
            print_report(
                dry_run=False,
                backup=False,
                backup_name=None,
                items=[],  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_invalid_backup_name(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("backup_name must be a string"),
            ),
        ):
            print_report(
                dry_run=False,
                backup=True,
                backup_name=123,  # type: ignore[arg-type]
                items=(),
            )

        print_message.assert_not_called()

    def test_rejects_empty_backup_name(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                ValueError,
                ("backup_name cannot be empty"),
            ),
        ):
            print_report(
                dry_run=False,
                backup=True,
                backup_name=" ",
                items=(),
            )

        print_message.assert_not_called()


class ParseArgsTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = parse_args([])

        self.assertIsInstance(
            args,
            argparse.Namespace,
        )
        self.assertFalse(args.dry_run)
        self.assertFalse(args.yes)
        self.assertFalse(args.no_backup)

    def test_parses_all_options(self) -> None:
        args = parse_args(
            [
                "--dry-run",
                "--yes",
                "--no-backup",
            ]
        )

        self.assertTrue(args.dry_run)
        self.assertTrue(args.yes)
        self.assertTrue(args.no_backup)

    def test_rejects_unknown_argument(self) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--unknown",
                ]
            )


class MainTests(unittest.TestCase):
    def make_args(
        self,
        *,
        dry_run: bool = False,
        yes: bool = True,
        no_backup: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            dry_run=dry_run,
            yes=yes,
            no_backup=no_backup,
        )

    def test_requires_confirmation_for_real_reset(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(
                    dry_run=False,
                    yes=False,
                ),
            ) as parse,
            patch(f"{MODULE}.run_reset") as run_reset_call,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        parse.assert_called_once_with([])
        run_reset_call.assert_not_called()
        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("This command removes generated Betabox media."),
                call(),
                call("Run a preview first:"),
                call("  betabox reset --dry-run"),
                call(),
                call("To perform the reset:"),
                call("  betabox reset --yes"),
                call(),
            ],
        )

    def test_dry_run_does_not_require_yes(
        self,
    ) -> None:
        items = (
            make_item(
                action="would remove",
                message="dry run",
            ),
        )

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(
                    dry_run=True,
                    yes=False,
                ),
            ),
            patch(
                f"{MODULE}.run_reset",
                return_value=(
                    None,
                    items,
                ),
            ) as run_reset_call,
            patch(
                f"{MODULE}.print_report",
                return_value=True,
            ) as print_report_call,
        ):
            result = main(
                [
                    "--dry-run",
                ]
            )

        self.assertEqual(result, 0)
        run_reset_call.assert_called_once_with(
            dry_run=True,
            backup=True,
        )
        print_report_call.assert_called_once_with(
            dry_run=True,
            backup=True,
            backup_name=None,
            items=items,
        )

    def test_runs_confirmed_reset_with_backup(
        self,
    ) -> None:
        items = (make_item(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                return_value=(
                    "backup-001",
                    items,
                ),
            ) as run_reset_call,
            patch(
                f"{MODULE}.print_report",
                return_value=True,
            ) as print_report_call,
        ):
            result = main(
                [
                    "--yes",
                ]
            )

        self.assertEqual(result, 0)
        run_reset_call.assert_called_once_with(
            dry_run=False,
            backup=True,
        )
        print_report_call.assert_called_once_with(
            dry_run=False,
            backup=True,
            backup_name="backup-001",
            items=items,
        )

    def test_runs_without_backup(self) -> None:
        items = (make_item(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(no_backup=True),
            ),
            patch(
                f"{MODULE}.run_reset",
                return_value=(
                    None,
                    items,
                ),
            ) as run_reset_call,
            patch(
                f"{MODULE}.print_report",
                return_value=True,
            ) as print_report_call,
        ):
            result = main(
                [
                    "--yes",
                    "--no-backup",
                ]
            )

        self.assertEqual(result, 0)
        run_reset_call.assert_called_once_with(
            dry_run=False,
            backup=False,
        )
        print_report_call.assert_called_once_with(
            dry_run=False,
            backup=False,
            backup_name=None,
            items=items,
        )

    def test_returns_one_when_report_fails(
        self,
    ) -> None:
        items = (
            make_item(
                ok=False,
                action="remove failed",
            ),
        )

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                return_value=(
                    "backup-001",
                    items,
                ),
            ),
            patch(
                f"{MODULE}.print_report",
                return_value=False,
            ),
        ):
            result = main([])

        self.assertEqual(result, 1)

    def test_returns_one_for_reset_type_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                side_effect=TypeError("invalid reset"),
            ),
            patch(f"{MODULE}.print_report") as print_report_call,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid reset")
        print_report_call.assert_not_called()

    def test_returns_one_for_reset_value_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                side_effect=ValueError("invalid configuration"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid configuration")

    def test_returns_one_for_reset_os_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                side_effect=OSError("backup failed"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("backup failed")

    def test_returns_one_for_report_validation_error(
        self,
    ) -> None:
        items = (make_item(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                return_value=(
                    "backup-001",
                    items,
                ),
            ),
            patch(
                f"{MODULE}.print_report",
                side_effect=ValueError("invalid report"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid report")

    def test_unexpected_reset_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )

    def test_unexpected_report_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")
        items = (make_item(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_reset",
                return_value=(
                    "backup-001",
                    items,
                ),
            ),
            patch(
                f"{MODULE}.print_report",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
