from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.services.backup_checks.models import (
    BackupItem,
    BackupReport,
)


class BackupItemTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        item = BackupItem(
            source="/home/student",
            destination=("/var/backups/test/home/student"),
            copied=True,
            message="copied",
        )

        self.assertEqual(
            item.to_dict(),
            {
                "source": "/home/student",
                "destination": ("/var/backups/test/home/student"),
                "copied": True,
                "message": "copied",
            },
        )

    def test_default_message(self) -> None:
        item = BackupItem(
            source="/source",
            destination="/destination",
            copied=False,
        )

        self.assertEqual(
            item.message,
            "",
        )

    def test_is_frozen(self) -> None:
        item = BackupItem(
            source="/source",
            destination="/destination",
            copied=True,
        )

        with self.assertRaises(FrozenInstanceError):
            item.copied = False  # type: ignore[misc]


class BackupReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.items = (
            BackupItem(
                source="/home/student",
                destination=("/var/backups/test/home/student"),
                copied=True,
                message="copied",
            ),
            BackupItem(
                source="/missing",
                destination=("/var/backups/test/missing"),
                copied=False,
                message="source missing",
            ),
        )

    def test_preserves_items_as_tuple(self) -> None:
        report = BackupReport(
            name="test",
            path="/var/backups/test",
            created_at="2026-08-05 14:30:00",
            hostname="Betabox-7eea",
            sdk_version="1.0.0",
            items=self.items,
        )

        self.assertIs(
            report.items,
            self.items,
        )
        self.assertIsInstance(
            report.items,
            tuple,
        )

    def test_to_dict_converts_items_to_list(self) -> None:
        report = BackupReport(
            name="test",
            path="/var/backups/test",
            created_at="2026-08-05 14:30:00",
            hostname="Betabox-7eea",
            sdk_version="1.0.0",
            items=self.items,
        )

        self.assertEqual(
            report.to_dict(),
            {
                "name": "test",
                "path": "/var/backups/test",
                "created_at": ("2026-08-05 14:30:00"),
                "hostname": "Betabox-7eea",
                "sdk_version": "1.0.0",
                "items": [
                    self.items[0].to_dict(),
                    self.items[1].to_dict(),
                ],
            },
        )

    def test_supports_empty_items(self) -> None:
        report = BackupReport(
            name="empty",
            path="/var/backups/empty",
            created_at="2026-08-05 14:30:00",
            hostname="Betabox-7eea",
            sdk_version="1.0.0",
            items=(),
        )

        self.assertEqual(
            report.to_dict()["items"],
            [],
        )

    def test_is_frozen(self) -> None:
        report = BackupReport(
            name="test",
            path="/var/backups/test",
            created_at="2026-08-05 14:30:00",
            hostname="Betabox-7eea",
            sdk_version="1.0.0",
            items=self.items,
        )

        with self.assertRaises(FrozenInstanceError):
            report.name = "changed"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
