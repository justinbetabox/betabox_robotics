from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.services.restore_checks.models import (
    RestoreItem,
)


class RestoreItemTests(unittest.TestCase):
    def test_create_restored_item(self) -> None:
        item = RestoreItem(
            source=("/backups/test-backup/home/student/file.txt"),
            destination="/home/student/file.txt",
            restored=True,
            message="restored",
        )

        self.assertEqual(
            item.source,
            ("/backups/test-backup/home/student/file.txt"),
        )
        self.assertEqual(
            item.destination,
            "/home/student/file.txt",
        )
        self.assertTrue(item.restored)
        self.assertEqual(
            item.message,
            "restored",
        )

    def test_create_skipped_item(self) -> None:
        item = RestoreItem(
            source=("/backups/test-backup/home/student/file.txt"),
            destination="/home/student/file.txt",
            restored=False,
            message="source missing in backup",
        )

        self.assertFalse(item.restored)
        self.assertEqual(
            item.message,
            "source missing in backup",
        )

    def test_default_message(self) -> None:
        item = RestoreItem(
            source="/source",
            destination="/destination",
            restored=False,
        )

        self.assertEqual(
            item.message,
            "",
        )

    def test_to_dict(self) -> None:
        item = RestoreItem(
            source=("/backups/test-backup/home/student/file.txt"),
            destination="/home/student/file.txt",
            restored=True,
            message="restored",
        )

        self.assertEqual(
            item.to_dict(),
            {
                "source": ("/backups/test-backup/home/student/file.txt"),
                "destination": ("/home/student/file.txt"),
                "restored": True,
                "message": "restored",
            },
        )

    def test_to_dict_includes_empty_message(self) -> None:
        item = RestoreItem(
            source="/source",
            destination="/destination",
            restored=False,
        )

        self.assertEqual(
            item.to_dict(),
            {
                "source": "/source",
                "destination": "/destination",
                "restored": False,
                "message": "",
            },
        )

    def test_is_frozen(self) -> None:
        item = RestoreItem(
            source="/source",
            destination="/destination",
            restored=True,
        )

        with self.assertRaises(FrozenInstanceError):
            item.restored = False  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        item = RestoreItem(
            source="/source",
            destination="/destination",
            restored=True,
        )

        self.assertFalse(
            hasattr(
                item,
                "__dict__",
            )
        )


if __name__ == "__main__":
    unittest.main()
