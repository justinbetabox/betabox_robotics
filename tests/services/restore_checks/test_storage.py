from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.services.restore_checks.models import (
    RestoreItem,
)
from betabox_robotics.services.restore_checks.storage import (
    backup_source_path,
    restore_item,
)

MODULE = "betabox_robotics.services.restore_checks.storage"


class BackupSourcePathTests(unittest.TestCase):
    def test_maps_absolute_destination_into_backup(
        self,
    ) -> None:
        result = backup_source_path(
            "/backups/test-backup",
            "/home/student/file.txt",
        )

        self.assertEqual(
            result,
            Path("/backups/test-backup/home/student/file.txt"),
        )

    def test_maps_relative_destination_into_backup(
        self,
    ) -> None:
        result = backup_source_path(
            "/backups/test-backup",
            "home/student/file.txt",
        )

        self.assertEqual(
            result,
            Path("/backups/test-backup/home/student/file.txt"),
        )

    def test_accepts_path_values(self) -> None:
        backup_dir = Path("/backups/test-backup")
        destination = Path("/home/student")

        result = backup_source_path(
            backup_dir,
            destination,
        )

        self.assertEqual(
            result,
            backup_dir / "home/student",
        )

    def test_preserves_nested_destination(self) -> None:
        result = backup_source_path(
            "/backup",
            "/opt/betabox/data/config.json",
        )

        self.assertEqual(
            result,
            Path("/backup/opt/betabox/data/config.json"),
        )

    def test_rejects_invalid_backup_directory(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("backup_dir must be a string or Path"),
        ):
            backup_source_path(
                True,  # type: ignore[arg-type]
                "/destination",
            )

    def test_rejects_invalid_destination(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("destination must be a string or Path"),
        ):
            backup_source_path(
                "/backup",
                True,  # type: ignore[arg-type]
            )


class RestoreItemTests(unittest.TestCase):
    def test_reports_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup_dir = root / "backup"
            destination = root / "restore" / "file.txt"

            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

            source = backup_source_path(
                backup_dir,
                destination,
            )

        self.assertEqual(
            item,
            RestoreItem(
                source=str(source),
                destination=str(destination),
                restored=False,
                message="source missing in backup",
            ),
        )

    def test_dry_run_reports_existing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup_dir = root / "backup"
            destination = root / "restore" / "file.txt"
            source = backup_source_path(
                backup_dir,
                destination,
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                "backup contents",
                encoding="utf-8",
            )

            item = restore_item(
                backup_dir,
                destination,
                dry_run=True,
            )

        self.assertEqual(
            item,
            RestoreItem(
                source=str(source),
                destination=str(destination),
                restored=False,
                message="dry run",
            ),
        )
        self.assertFalse(destination.exists())

    def test_dry_run_reports_existing_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup_dir = root / "backup"
            destination = root / "restore"
            source = backup_source_path(
                backup_dir,
                destination,
            )
            source.mkdir(parents=True)

            item = restore_item(
                backup_dir,
                destination,
                dry_run=True,
            )

        self.assertFalse(item.restored)
        self.assertEqual(
            item.message,
            "dry run",
        )

    def test_restores_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup_dir = root / "backup"
            destination = root / "restore" / "file.txt"
            source = backup_source_path(
                backup_dir,
                destination,
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                "backup contents",
                encoding="utf-8",
            )

            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

            self.assertTrue(destination.is_file())
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "backup contents",
            )

        self.assertEqual(
            item,
            RestoreItem(
                source=str(source),
                destination=str(destination),
                restored=True,
                message="restored",
            ),
        )

    def test_restores_directory_recursively(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup_dir = root / "backup"
            destination = root / "restore"
            source = backup_source_path(
                backup_dir,
                destination,
            )
            nested = source / "nested" / "file.txt"
            nested.parent.mkdir(parents=True)
            nested.write_text(
                "nested contents",
                encoding="utf-8",
            )

            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

            restored = destination / "nested" / "file.txt"

            self.assertTrue(restored.is_file())
            self.assertEqual(
                restored.read_text(encoding="utf-8"),
                "nested contents",
            )

        self.assertTrue(item.restored)
        self.assertEqual(
            item.message,
            "restored",
        )

    def test_merges_existing_destination_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup_dir = root / "backup"
            destination = root / "restore"
            source = backup_source_path(
                backup_dir,
                destination,
            )

            source.mkdir(parents=True)
            (source / "new.txt").write_text(
                "new",
                encoding="utf-8",
            )

            destination.mkdir(parents=True)
            (destination / "existing.txt").write_text(
                "existing",
                encoding="utf-8",
            )

            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

            self.assertTrue((destination / "existing.txt").is_file())
            self.assertTrue((destination / "new.txt").is_file())

        self.assertTrue(item.restored)

    def test_creates_destination_parent(self) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student/file.txt")
        source = backup_dir / "home/student/file.txt"

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
            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        copy2.assert_called_once_with(
            source,
            destination,
        )
        self.assertTrue(item.restored)

    def test_uses_copytree_for_directory(self) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student")
        source = backup_dir / "home/student"

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
            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

        copytree.assert_called_once_with(
            source,
            destination,
            dirs_exist_ok=True,
        )
        copy2.assert_not_called()
        self.assertTrue(item.restored)

    def test_uses_copy2_for_file(self) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student/file.txt")
        source = backup_dir / "home/student/file.txt"

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
            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

        copy2.assert_called_once_with(
            source,
            destination,
        )
        copytree.assert_not_called()
        self.assertTrue(item.restored)

    def test_reports_parent_creation_error(self) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student/file.txt")

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
            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

        self.assertFalse(item.restored)
        self.assertEqual(
            item.message,
            "permission denied",
        )

    def test_reports_file_copy_error(self) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student/file.txt")

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
            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

        self.assertFalse(item.restored)
        self.assertEqual(
            item.message,
            "copy failed",
        )

    def test_reports_directory_copy_error(
        self,
    ) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student")

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
            item = restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

        self.assertFalse(item.restored)
        self.assertEqual(
            item.message,
            "copy failed",
        )

    def test_unexpected_copy_error_propagates(
        self,
    ) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student/file.txt")
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
            restore_item(
                backup_dir,
                destination,
                dry_run=False,
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_missing_source_precedes_dry_run(
        self,
    ) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student")

        with patch.object(
            Path,
            "exists",
            return_value=False,
        ):
            item = restore_item(
                backup_dir,
                destination,
                dry_run=True,
            )

        self.assertEqual(
            item.message,
            "source missing in backup",
        )

    def test_dry_run_does_not_create_parent_or_copy(
        self,
    ) -> None:
        backup_dir = Path("/backups/test")
        destination = Path("/home/student/file.txt")

        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(Path, "mkdir") as mkdir,
            patch(f"{MODULE}.shutil.copy2") as copy2,
            patch(f"{MODULE}.shutil.copytree") as copytree,
        ):
            item = restore_item(
                backup_dir,
                destination,
                dry_run=True,
            )

        self.assertEqual(
            item.message,
            "dry run",
        )
        mkdir.assert_not_called()
        copy2.assert_not_called()
        copytree.assert_not_called()

    def test_rejects_non_boolean_dry_run(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "dry_run must be a boolean",
        ):
            restore_item(
                "/backup",
                "/destination",
                dry_run=1,  # type: ignore[arg-type]
            )

    def test_validates_dry_run_before_paths(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.validate_path") as validate_path,
            self.assertRaisesRegex(
                TypeError,
                "dry_run must be a boolean",
            ),
        ):
            restore_item(
                True,  # type: ignore[arg-type]
                True,  # type: ignore[arg-type]
                dry_run="yes",  # type: ignore[arg-type]
            )

        validate_path.assert_not_called()

    def test_rejects_invalid_backup_directory(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("backup_dir must be a string or Path"),
        ):
            restore_item(
                True,  # type: ignore[arg-type]
                "/destination",
                dry_run=False,
            )

    def test_rejects_invalid_destination(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("destination must be a string or Path"),
        ):
            restore_item(
                "/backup",
                True,  # type: ignore[arg-type]
                dry_run=False,
            )


if __name__ == "__main__":
    unittest.main()
