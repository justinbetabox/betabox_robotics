from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.backup import (
    create_backup,
    list_backups,
    main,
    print_backups,
    print_report,
    source_paths,
    timestamp,
)
from betabox_robotics.services.backup_checks import (
    BackupItem,
    BackupReport,
)
from betabox_robotics.version import __version__

MODULE = "betabox_robotics.services.backup"


def make_item(
    *,
    copied: bool = True,
) -> BackupItem:
    return BackupItem(
        source="/home/student",
        destination=("/backups/test-backup/home/student"),
        copied=copied,
        message=("copied" if copied else "source missing"),
    )


def make_report() -> BackupReport:
    return BackupReport(
        name="test-backup",
        path="/backups/test-backup",
        created_at="2026-08-05 14:30:00",
        hostname="Betabox-7eea",
        sdk_version=__version__,
        items=(
            make_item(),
            make_item(copied=False),
        ),
    )


class TimestampTests(unittest.TestCase):
    def test_formats_current_time(self) -> None:
        with patch(
            f"{MODULE}.time.strftime",
            return_value="20260805-143000",
        ) as strftime:
            result = timestamp()

        self.assertEqual(
            result,
            "20260805-143000",
        )
        strftime.assert_called_once_with("%Y%m%d-%H%M%S")


class SourcePathsTests(unittest.TestCase):
    def test_returns_configured_sources_as_tuple(
        self,
    ) -> None:
        expected = tuple(
            Path(path).expanduser()
            for path in (DEFAULT_PLATFORM_CONFIG.paths.backup_sources)
        )

        result = source_paths()

        self.assertEqual(
            result,
            expected,
        )
        self.assertIsInstance(
            result,
            tuple,
        )

    def test_validates_each_source_path(self) -> None:
        sources = DEFAULT_PLATFORM_CONFIG.paths.backup_sources

        with patch(
            f"{MODULE}.validate_path",
            side_effect=[
                Path(f"/validated/{index}") for index, _ in enumerate(sources)
            ],
        ) as validate_path:
            result = source_paths()

        self.assertEqual(
            result,
            tuple(Path(f"/validated/{index}") for index, _ in enumerate(sources)),
        )
        self.assertEqual(
            validate_path.call_args_list,
            [
                call(
                    source,
                    name="backup source",
                )
                for source in sources
            ],
        )

    def test_rejects_invalid_config_before_paths(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.validate_path") as validate_path,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            source_paths(
                object()  # type: ignore[arg-type]
            )

        validate_path.assert_not_called()


class CreateBackupTests(unittest.TestCase):
    def test_creates_named_backup(self) -> None:
        backup_root = Path("/backups")
        backup_dir = backup_root / "test-backup"
        sources = (
            Path("/home/student"),
            Path("/etc/betabox"),
        )
        items = (
            BackupItem(
                source=str(sources[0]),
                destination=(f"{backup_dir}/home/student"),
                copied=True,
                message="copied",
            ),
            BackupItem(
                source=str(sources[1]),
                destination=(f"{backup_dir}/etc/betabox"),
                copied=False,
                message="source missing",
            ),
        )

        with (
            patch(
                f"{MODULE}.validate_path",
                return_value=backup_root,
            ) as validate_path,
            patch.object(Path, "mkdir") as mkdir,
            patch(
                f"{MODULE}.source_paths",
                return_value=sources,
            ) as get_sources,
            patch(
                f"{MODULE}.copy_item",
                side_effect=items,
            ) as copy_item,
            patch(
                f"{MODULE}.time.strftime",
                return_value=("2026-08-05 14:30:00"),
            ) as strftime,
            patch(
                f"{MODULE}.socket.gethostname",
                return_value="Betabox-7eea",
            ) as gethostname,
            patch(f"{MODULE}.write_manifest") as write_manifest,
        ):
            report = create_backup("test-backup")

        validate_path.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG.paths.backup_root,
            name="backup_root",
        )
        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=False,
        )
        get_sources.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        self.assertEqual(
            copy_item.call_args_list,
            [
                call(
                    sources[0],
                    backup_dir,
                ),
                call(
                    sources[1],
                    backup_dir,
                ),
            ],
        )
        strftime.assert_called_once_with("%Y-%m-%d %H:%M:%S")
        gethostname.assert_called_once_with()

        self.assertEqual(
            report,
            BackupReport(
                name="test-backup",
                path=str(backup_dir),
                created_at=("2026-08-05 14:30:00"),
                hostname="Betabox-7eea",
                sdk_version=__version__,
                items=items,
            ),
        )
        write_manifest.assert_called_once_with(
            report,
            backup_dir,
        )

    def test_uses_generated_timestamp_name(self) -> None:
        backup_root = Path("/backups")

        with (
            patch(
                f"{MODULE}.timestamp",
                return_value="20260805-143000",
            ) as generate_timestamp,
            patch(
                f"{MODULE}.validate_path",
                return_value=backup_root,
            ),
            patch.object(Path, "mkdir"),
            patch(
                f"{MODULE}.source_paths",
                return_value=(),
            ),
            patch(
                f"{MODULE}.time.strftime",
                return_value=("2026-08-05 14:30:00"),
            ),
            patch(
                f"{MODULE}.socket.gethostname",
                return_value="Betabox-7eea",
            ),
            patch(f"{MODULE}.write_manifest"),
        ):
            report = create_backup()

        generate_timestamp.assert_called_once_with()
        self.assertEqual(
            report.name,
            "20260805-143000",
        )
        self.assertEqual(
            report.path,
            "/backups/20260805-143000",
        )

    def test_validates_custom_name(self) -> None:
        backup_root = Path("/backups")

        with (
            patch(
                f"{MODULE}.validate_backup_name",
                return_value="clean-name",
            ) as validate_name,
            patch(
                f"{MODULE}.validate_path",
                return_value=backup_root,
            ),
            patch.object(Path, "mkdir"),
            patch(
                f"{MODULE}.source_paths",
                return_value=(),
            ),
            patch(
                f"{MODULE}.time.strftime",
                return_value=("2026-08-05 14:30:00"),
            ),
            patch(
                f"{MODULE}.socket.gethostname",
                return_value="Betabox-7eea",
            ),
            patch(f"{MODULE}.write_manifest"),
        ):
            report = create_backup(" raw-name ")

        validate_name.assert_called_once_with(" raw-name ")
        self.assertEqual(
            report.name,
            "clean-name",
        )

    def test_validates_generated_name(self) -> None:
        with (
            patch(
                f"{MODULE}.timestamp",
                return_value="generated-name",
            ),
            patch(
                f"{MODULE}.validate_backup_name",
                side_effect=ValueError("invalid generated name"),
            ) as validate_name,
            patch.object(Path, "mkdir") as mkdir,
            self.assertRaisesRegex(
                ValueError,
                "invalid generated name",
            ),
        ):
            create_backup()

        validate_name.assert_called_once_with("generated-name")
        mkdir.assert_not_called()

    def test_rejects_invalid_config_before_name_generation(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.timestamp") as generate_timestamp,
            patch.object(Path, "mkdir") as mkdir,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            create_backup(
                config=object(),  # type: ignore[arg-type]
            )

        generate_timestamp.assert_not_called()
        mkdir.assert_not_called()

    def test_directory_creation_error_propagates(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.validate_path",
                return_value=Path("/backups"),
            ),
            patch.object(
                Path,
                "mkdir",
                side_effect=OSError("permission denied"),
            ),
            patch(f"{MODULE}.source_paths") as get_sources,
            self.assertRaisesRegex(
                OSError,
                "permission denied",
            ),
        ):
            create_backup("test-backup")

        get_sources.assert_not_called()

    def test_file_exists_error_propagates(self) -> None:
        error = FileExistsError("already exists")

        with (
            patch(
                f"{MODULE}.validate_path",
                return_value=Path("/backups"),
            ),
            patch.object(
                Path,
                "mkdir",
                side_effect=error,
            ),
            self.assertRaises(FileExistsError) as context,
        ):
            create_backup("test-backup")

        self.assertIs(
            context.exception,
            error,
        )

    def test_copy_results_are_stored_as_tuple(
        self,
    ) -> None:
        item = make_item()

        with (
            patch(
                f"{MODULE}.validate_path",
                return_value=Path("/backups"),
            ),
            patch.object(Path, "mkdir"),
            patch(
                f"{MODULE}.source_paths",
                return_value=(Path("/source"),),
            ),
            patch(
                f"{MODULE}.copy_item",
                return_value=item,
            ),
            patch(
                f"{MODULE}.time.strftime",
                return_value=("2026-08-05 14:30:00"),
            ),
            patch(
                f"{MODULE}.socket.gethostname",
                return_value="Betabox-7eea",
            ),
            patch(f"{MODULE}.write_manifest"),
        ):
            report = create_backup("test-backup")

        self.assertEqual(
            report.items,
            (item,),
        )
        self.assertIsInstance(
            report.items,
            tuple,
        )

    def test_manifest_error_propagates(self) -> None:
        error = OSError("manifest write failed")

        with (
            patch(
                f"{MODULE}.validate_path",
                return_value=Path("/backups"),
            ),
            patch.object(Path, "mkdir"),
            patch(
                f"{MODULE}.source_paths",
                return_value=(),
            ),
            patch(
                f"{MODULE}.time.strftime",
                return_value=("2026-08-05 14:30:00"),
            ),
            patch(
                f"{MODULE}.socket.gethostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.write_manifest",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            create_backup("test-backup")

        self.assertIs(
            context.exception,
            error,
        )


class ListBackupsTests(unittest.TestCase):
    def test_delegates_to_storage(self) -> None:
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

    def test_rejects_invalid_config_before_storage(
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


class PrintReportTests(unittest.TestCase):
    def test_prints_report(self) -> None:
        report = make_report()

        with patch("builtins.print") as print_message:
            print_report(report)

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Backup"),
                call("=============="),
                call(),
                call(f"Name: {report.name}"),
                call(f"Path: {report.path}"),
                call(f"Created: {report.created_at}"),
                call(f"Host: {report.hostname}"),
                call(f"SDK: {report.sdk_version}"),
                call(),
                call("Items"),
                call("-----"),
                call(f"[COPIED] {report.items[0].source}"),
                call(f"        -> {report.items[0].destination}"),
                call(f"        {report.items[0].message}"),
                call(f"[SKIPPED] {report.items[1].source}"),
                call(f"        -> {report.items[1].destination}"),
                call(f"        {report.items[1].message}"),
                call(),
            ],
        )

    def test_does_not_print_empty_message(self) -> None:
        item = BackupItem(
            source="/source",
            destination="/destination",
            copied=True,
            message="",
        )
        report = BackupReport(
            name="test",
            path="/backups/test",
            created_at="created",
            hostname="host",
            sdk_version="version",
            items=(item,),
        )

        with patch("builtins.print") as print_message:
            print_report(report)

        self.assertNotIn(
            call("        "),
            print_message.call_args_list,
        )

    def test_rejects_invalid_report_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "report must be a BackupReport",
            ),
        ):
            print_report(
                object()  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


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


class MainTests(unittest.TestCase):
    def test_list_mode_prints_backups(self) -> None:
        backups = (Path("/backups/new"),)

        with (
            patch(
                f"{MODULE}.list_backups",
                return_value=backups,
            ) as list_backups_call,
            patch(f"{MODULE}.print_backups") as print_backups_call,
            patch(f"{MODULE}.create_backup") as create_backup_call,
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
        create_backup_call.assert_not_called()

    def test_create_mode_prints_report(self) -> None:
        report = make_report()

        with (
            patch(
                f"{MODULE}.create_backup",
                return_value=report,
            ) as create_backup_call,
            patch(f"{MODULE}.print_report") as print_report_call,
        ):
            result = main(
                [
                    "--name",
                    "test-backup",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        create_backup_call.assert_called_once_with("test-backup")
        print_report_call.assert_called_once_with(report)

    def test_create_mode_without_name(self) -> None:
        report = make_report()

        with (
            patch(
                f"{MODULE}.create_backup",
                return_value=report,
            ) as create_backup_call,
            patch(f"{MODULE}.print_report"),
        ):
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        create_backup_call.assert_called_once_with(None)

    def test_returns_one_for_validation_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.create_backup",
                side_effect=ValueError("backup name is invalid"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(
                [
                    "--name",
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
                f"{MODULE}.create_backup",
                side_effect=TypeError("invalid type"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("invalid type")

    def test_reports_existing_named_backup(self) -> None:
        with (
            patch(
                f"{MODULE}.create_backup",
                side_effect=FileExistsError,
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(
                [
                    "--name",
                    "test-backup",
                ]
            )

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("Backup already exists: test-backup")

    def test_reports_generated_name_collision(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.create_backup",
                side_effect=FileExistsError,
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with(
            "Backup already exists: generated timestamp"
        )

    def test_reports_operating_system_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.create_backup",
                side_effect=OSError("permission denied"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with(
            "Unable to create backup: permission denied"
        )

    def test_unexpected_error_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.create_backup",
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
