from __future__ import annotations

import unittest
from collections import namedtuple
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.system_checks.disk import (
    collect_disk_status,
)

MODULE = "betabox_robotics.services.system_checks.disk"

DiskUsage = namedtuple(
    "DiskUsage",
    [
        "total",
        "used",
        "free",
    ],
)


def make_config(
    *,
    high_percent: float,
    critical_percent: float,
):
    disk = replace(
        DEFAULT_PLATFORM_CONFIG.health.disk,
        high_percent=high_percent,
        critical_percent=critical_percent,
    )
    health = replace(
        DEFAULT_PLATFORM_CONFIG.health,
        disk=disk,
    )

    return replace(
        DEFAULT_PLATFORM_CONFIG,
        health=health,
    )


def make_usage(
    *,
    total_gb: float,
    free_gb: float,
) -> DiskUsage:
    gb = 1024**3

    total = int(total_gb * gb)
    free = int(free_gb * gb)

    return DiskUsage(
        total=total,
        used=total - free,
        free=free,
    )


class CollectDiskStatusTests(unittest.TestCase):
    def test_collects_disk_usage(self) -> None:
        path = Path("/tmp")

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=make_usage(
                total_gb=10.0,
                free_gb=6.0,
            ),
        ) as disk_usage:
            status = collect_disk_status(path)

        disk_usage.assert_called_once_with(path)

        self.assertEqual(
            status.path,
            "/tmp",
        )
        self.assertEqual(
            status.total_gb,
            10.0,
        )
        self.assertEqual(
            status.free_gb,
            6.0,
        )
        self.assertEqual(
            status.used_percent,
            40.0,
        )
        self.assertEqual(
            status.state,
            "normal",
        )
        self.assertIsNone(status.error)

    def test_accepts_string_path(self) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=make_usage(
                total_gb=8.0,
                free_gb=4.0,
            ),
        ) as disk_usage:
            status = collect_disk_status("/var")

        disk_usage.assert_called_once_with(Path("/var"))
        self.assertEqual(
            status.path,
            "/var",
        )

    def test_uses_configured_default_path(self) -> None:
        selected_path = DEFAULT_PLATFORM_CONFIG.health.disk_path

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=make_usage(
                total_gb=16.0,
                free_gb=8.0,
            ),
        ) as disk_usage:
            status = collect_disk_status()

        disk_usage.assert_called_once_with(Path(selected_path))
        self.assertEqual(
            status.path,
            str(Path(selected_path)),
        )

    def test_explicit_path_overrides_config(self) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=make_usage(
                total_gb=16.0,
                free_gb=8.0,
            ),
        ) as disk_usage:
            collect_disk_status(
                "/custom",
                config=DEFAULT_PLATFORM_CONFIG,
            )

        disk_usage.assert_called_once_with(Path("/custom"))

    def test_rounds_gigabytes_to_one_decimal(self) -> None:
        usage = DiskUsage(
            total=int(10.56 * 1024**3),
            used=int(4.22 * 1024**3),
            free=int(6.34 * 1024**3),
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=usage,
        ):
            status = collect_disk_status("/")

        self.assertEqual(
            status.total_gb,
            10.6,
        )
        self.assertEqual(
            status.free_gb,
            6.3,
        )

    def test_rounds_used_percent_to_one_decimal(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=3000,
                used=2000,
                free=1000,
            ),
        ):
            status = collect_disk_status("/")

        self.assertEqual(
            status.used_percent,
            66.7,
        )

    def test_calculates_used_from_total_and_free(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=1000,
                used=999,
                free=400,
            ),
        ):
            status = collect_disk_status("/")

        self.assertEqual(
            status.used_percent,
            60.0,
        )

    def test_classifies_normal_disk_usage(self) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=1000,
                used=699,
                free=301,
            ),
        ):
            status = collect_disk_status(
                "/",
                config=config,
            )

        self.assertEqual(
            status.state,
            "normal",
        )

    def test_classifies_high_at_threshold(self) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=1000,
                used=700,
                free=300,
            ),
        ):
            status = collect_disk_status(
                "/",
                config=config,
            )

        self.assertEqual(
            status.used_percent,
            70.0,
        )
        self.assertEqual(
            status.state,
            "high",
        )

    def test_classifies_between_thresholds(self) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=1000,
                used=800,
                free=200,
            ),
        ):
            status = collect_disk_status(
                "/",
                config=config,
            )

        self.assertEqual(
            status.state,
            "high",
        )

    def test_classifies_critical_at_threshold(
        self,
    ) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=1000,
                used=900,
                free=100,
            ),
        ):
            status = collect_disk_status(
                "/",
                config=config,
            )

        self.assertEqual(
            status.used_percent,
            90.0,
        )
        self.assertEqual(
            status.state,
            "critical",
        )

    def test_classifies_above_critical(self) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=1000,
                used=950,
                free=50,
            ),
        ):
            status = collect_disk_status(
                "/",
                config=config,
            )

        self.assertEqual(
            status.state,
            "critical",
        )

    def test_supports_empty_disk(self) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=1000,
                used=0,
                free=1000,
            ),
        ):
            status = collect_disk_status("/")

        self.assertEqual(
            status.used_percent,
            0.0,
        )
        self.assertEqual(
            status.state,
            "normal",
        )

    def test_returns_unknown_for_disk_usage_error(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            side_effect=OSError("path unavailable"),
        ):
            status = collect_disk_status("/missing")

        self.assertEqual(
            status.path,
            "/missing",
        )
        self.assertIsNone(status.total_gb)
        self.assertIsNone(status.free_gb)
        self.assertIsNone(status.used_percent)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "path unavailable",
        )

    def test_returns_unknown_for_zero_total(self) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=0,
                used=0,
                free=0,
            ),
        ):
            status = collect_disk_status("/")

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "disk total must be greater than 0",
        )

    def test_returns_unknown_for_negative_total(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=DiskUsage(
                total=-1,
                used=0,
                free=0,
            ),
        ):
            status = collect_disk_status("/")

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "disk total must be greater than 0",
        )

    def test_rejects_invalid_config_before_disk_usage(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.shutil.disk_usage") as disk_usage,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_disk_status(
                config=object(),  # type: ignore[arg-type]
            )

        disk_usage.assert_not_called()

    def test_rejects_invalid_path_before_disk_usage(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.shutil.disk_usage") as disk_usage,
            self.assertRaisesRegex(
                TypeError,
                "path must be a string or Path",
            ),
        ):
            collect_disk_status(
                path=True,  # type: ignore[arg-type]
            )

        disk_usage.assert_not_called()

    def test_unexpected_threshold_error_propagates(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.validate_config",
                return_value=object(),
            ),
            patch(
                f"{MODULE}.shutil.disk_usage",
                return_value=make_usage(
                    total_gb=10.0,
                    free_gb=5.0,
                ),
            ),
            self.assertRaises(
                AttributeError,
            ),
        ):
            collect_disk_status("/")


if __name__ == "__main__":
    unittest.main()
