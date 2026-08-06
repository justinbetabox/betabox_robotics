from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from betabox_robotics.services.backup_checks.models import (
    BackupItem,
    BackupReport,
)
from betabox_robotics.services.backup_checks.storage import (
    copy_item,
    list_backup_directories,
    write_manifest,
)

MODULE = "betabox_robotics.services.backup_checks.storage"


def make_report() -> BackupReport:
    return BackupReport(
        name="test-backup",
        path="/backups/test-backup",
        created_at="2026-08-05 14:30:00",
        hostname="Betabox-7eea",
        sdk_version="1.0.0",
        items=(
            BackupItem(
                source="/home/student/file.txt",
                destination=("/backups/test-backup/home/student/file.txt"),
                copied=True,
                message="copied",
            ),
        ),
    )


class CopyItemTests(unittest.TestCase):
    def test_reports_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "missing"
            backup_dir = root / "backup"

            item = copy_item(
                source,
                backup_dir,
            )

        self.assertEqual(
            item.source,
            str(source),
        )
        self.assertEqual(
            item.destination,
            str(backup_dir / source.as_posix().lstrip("/")),
        )
        self.assertFalse(item.copied)
        self.assertEqual(
            item.message,
            "source missing",
        )

    def test_copies_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source" / "file.txt"
            source.parent.mkdir(parents=True)
            source.write_text(
                "backup contents",
                encoding="utf-8",
            )

            backup_dir = root / "backup"

            item = copy_item(
                source,
                backup_dir,
            )

            destination = backup_dir / source.as_posix().lstrip("/")

            self.assertTrue(destination.is_file())
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "backup contents",
            )

        self.assertTrue(item.copied)
        self.assertEqual(
            item.source,
            str(source),
        )
        self.assertEqual(
            item.destination,
            str(destination),
        )
        self.assertEqual(
            item.message,
            "copied",
        )

    def test_copies_directory_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            nested = source / "nested" / "file.txt"
            nested.parent.mkdir(parents=True)
            nested.write_text(
                "nested contents",
                encoding="utf-8",
            )

            backup_dir = root / "backup"

            item = copy_item(
                source,
                backup_dir,
            )

            destination = backup_dir / source.as_posix().lstrip("/")

            copied = destination / "nested" / "file.txt"

            self.assertTrue(copied.is_file())
            self.assertEqual(
                copied.read_text(encoding="utf-8"),
                "nested contents",
            )

        self.assertTrue(item.copied)
        self.assertEqual(
            item.message,
            "copied",
        )

    def test_merges_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            (source / "new.txt").write_text(
                "new",
                encoding="utf-8",
            )

            backup_dir = root / "backup"
            destination = backup_dir / source.as_posix().lstrip("/")
            destination.mkdir(parents=True)
            (destination / "existing.txt").write_text(
                "existing",
                encoding="utf-8",
            )

            item = copy_item(
                source,
                backup_dir,
            )

            self.assertTrue((destination / "existing.txt").is_file())
            self.assertTrue((destination / "new.txt").is_file())

        self.assertTrue(item.copied)

    def test_creates_destination_parent(self) -> None:
        source = Path("/home/student/file.txt")
        backup_dir = Path("/backups/test")
        destination = backup_dir / "home/student/file.txt"

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
            patch.object(Path, "mkdir") as mkdir,
            patch(f"{MODULE}.shutil.copy2") as copy2,
        ):
            item = copy_item(
                source,
                backup_dir,
            )

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        copy2.assert_called_once_with(
            source,
            destination,
        )
        self.assertTrue(item.copied)

    def test_uses_copytree_for_directory(self) -> None:
        source = Path("/home/student")
        backup_dir = Path("/backups/test")
        destination = backup_dir / "home/student"

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
            patch.object(Path, "mkdir"),
            patch(f"{MODULE}.shutil.copytree") as copytree,
            patch(f"{MODULE}.shutil.copy2") as copy2,
        ):
            item = copy_item(
                source,
                backup_dir,
            )

        copytree.assert_called_once_with(
            source,
            destination,
            dirs_exist_ok=True,
        )
        copy2.assert_not_called()
        self.assertTrue(item.copied)

    def test_uses_copy2_for_file(self) -> None:
        source = Path("/home/student/file.txt")
        backup_dir = Path("/backups/test")
        destination = backup_dir / "home/student/file.txt"

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
            patch.object(Path, "mkdir"),
            patch(f"{MODULE}.shutil.copytree") as copytree,
            patch(f"{MODULE}.shutil.copy2") as copy2,
        ):
            item = copy_item(
                source,
                backup_dir,
            )

        copy2.assert_called_once_with(
            source,
            destination,
        )
        copytree.assert_not_called()
        self.assertTrue(item.copied)

    def test_reports_parent_creation_error(self) -> None:
        source = Path("/home/student/file.txt")
        backup_dir = Path("/backups/test")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "mkdir",
                side_effect=OSError("permission denied"),
            ),
        ):
            item = copy_item(
                source,
                backup_dir,
            )

        self.assertFalse(item.copied)
        self.assertEqual(
            item.message,
            "permission denied",
        )

    def test_reports_file_copy_error(self) -> None:
        source = Path("/home/student/file.txt")
        backup_dir = Path("/backups/test")

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
            patch.object(Path, "mkdir"),
            patch(
                f"{MODULE}.shutil.copy2",
                side_effect=OSError("copy failed"),
            ),
        ):
            item = copy_item(
                source,
                backup_dir,
            )

        self.assertFalse(item.copied)
        self.assertEqual(
            item.message,
            "copy failed",
        )

    def test_reports_directory_copy_error(
        self,
    ) -> None:
        source = Path("/home/student")
        backup_dir = Path("/backups/test")

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
            patch.object(Path, "mkdir"),
            patch(
                f"{MODULE}.shutil.copytree",
                side_effect=OSError("copy failed"),
            ),
        ):
            item = copy_item(
                source,
                backup_dir,
            )

        self.assertFalse(item.copied)
        self.assertEqual(
            item.message,
            "copy failed",
        )

    def test_unexpected_copy_error_propagates(
        self,
    ) -> None:
        source = Path("/home/student/file.txt")
        backup_dir = Path("/backups/test")
        error = RuntimeError("programming error")

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
            patch.object(Path, "mkdir"),
            patch(
                f"{MODULE}.shutil.copy2",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            copy_item(
                source,
                backup_dir,
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_source(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "source must be a string or Path",
        ):
            copy_item(
                True,  # type: ignore[arg-type]
                "/backup",
            )

    def test_rejects_invalid_backup_directory(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("backup_dir must be a string or Path"),
        ):
            copy_item(
                "/source",
                True,  # type: ignore[arg-type]
            )


class WriteManifestTests(unittest.TestCase):
    def test_writes_manifest_json(self) -> None:
        report = make_report()

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)

            write_manifest(
                report,
                backup_dir,
            )

            manifest = backup_dir / "manifest.json"

            self.assertTrue(manifest.is_file())

            content = manifest.read_text(encoding="utf-8")

        self.assertTrue(content.endswith("\n"))
        self.assertEqual(
            json.loads(content),
            report.to_dict(),
        )

    def test_opens_manifest_with_utf8(self) -> None:
        report = make_report()
        backup_dir = Path("/backups/test")
        file = mock_open()

        with patch.object(
            Path,
            "open",
            file,
        ):
            write_manifest(
                report,
                backup_dir,
            )

        file.assert_called_once_with(
            "w",
            encoding="utf-8",
        )

    def test_writes_report_data_and_newline(self) -> None:
        report = make_report()
        backup_dir = Path("/backups/test")
        file = mock_open()

        with (
            patch.object(
                Path,
                "open",
                file,
            ),
            patch(f"{MODULE}.json.dump") as dump,
        ):
            write_manifest(
                report,
                backup_dir,
            )

        handle = file()
        dump.assert_called_once_with(
            report.to_dict(),
            handle,
            indent=2,
        )
        handle.write.assert_called_once_with("\n")

    def test_rejects_invalid_report_before_open(
        self,
    ) -> None:
        with (
            patch.object(Path, "open") as open_file,
            self.assertRaisesRegex(
                TypeError,
                ("report must be a BackupReport"),
            ),
        ):
            write_manifest(
                object(),  # type: ignore[arg-type]
                "/backups/test",
            )

        open_file.assert_not_called()

    def test_rejects_invalid_backup_directory_before_open(
        self,
    ) -> None:
        with (
            patch.object(Path, "open") as open_file,
            self.assertRaisesRegex(
                TypeError,
                ("backup_dir must be a string or Path"),
            ),
        ):
            write_manifest(
                make_report(),
                True,  # type: ignore[arg-type]
            )

        open_file.assert_not_called()

    def test_write_error_propagates(self) -> None:
        report = make_report()

        with (
            patch.object(
                Path,
                "open",
                side_effect=OSError("permission denied"),
            ),
            self.assertRaisesRegex(
                OSError,
                "permission denied",
            ),
        ):
            write_manifest(
                report,
                "/backups/test",
            )


class ListBackupDirectoriesTests(unittest.TestCase):
    def test_returns_empty_for_missing_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "missing"

            result = list_backup_directories(root)

        self.assertEqual(
            result,
            (),
        )

    def test_returns_only_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "20260805-120000"
            second = root / "20260805-130000"
            file = root / "manifest.json"

            first.mkdir()
            second.mkdir()
            file.write_text(
                "{}",
                encoding="utf-8",
            )

            result = list_backup_directories(root)

        self.assertEqual(
            result,
            (
                second,
                first,
            ),
        )

    def test_sorts_names_in_reverse_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            names = (
                "backup-a",
                "backup-c",
                "backup-b",
            )

            for name in names:
                (root / name).mkdir()

            result = list_backup_directories(root)

        self.assertEqual(
            tuple(path.name for path in result),
            (
                "backup-c",
                "backup-b",
                "backup-a",
            ),
        )

    def test_returns_tuple(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = list_backup_directories(temp_dir)

        self.assertIsInstance(
            result,
            tuple,
        )

    def test_returns_empty_for_iteration_error(
        self,
    ) -> None:
        root = Path("/backups")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "iterdir",
                side_effect=OSError("permission denied"),
            ),
        ):
            result = list_backup_directories(root)

        self.assertEqual(
            result,
            (),
        )

    def test_rejects_invalid_root_before_filesystem_access(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("backup_root must be a string or Path"),
            ),
        ):
            list_backup_directories(
                True  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_unexpected_iteration_error_propagates(
        self,
    ) -> None:
        root = Path("/backups")
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "iterdir",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            list_backup_directories(root)

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
