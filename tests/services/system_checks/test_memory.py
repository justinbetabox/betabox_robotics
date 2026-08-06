from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.system_checks.memory import (
    MEMINFO_PATH,
    collect_memory_status,
)

MODULE = "betabox_robotics.services.system_checks.memory"


def make_config(
    *,
    high_percent: float,
    critical_percent: float,
):
    memory = replace(
        DEFAULT_PLATFORM_CONFIG.health.memory,
        high_percent=high_percent,
        critical_percent=critical_percent,
    )
    health = replace(
        DEFAULT_PLATFORM_CONFIG.health,
        memory=memory,
    )

    return replace(
        DEFAULT_PLATFORM_CONFIG,
        health=health,
    )


def write_meminfo(
    path: Path,
    *,
    total_kb: int,
    available_kb: int,
    extra: str = "",
) -> None:
    path.write_text(
        (f"MemTotal:       {total_kb} kB\nMemAvailable:   {available_kb} kB\n{extra}"),
        encoding="utf-8",
    )


class CollectMemoryStatusTests(unittest.TestCase):
    def test_reads_memory_from_supplied_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1048576,
                available_kb=524288,
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.total_mb,
            1024,
        )
        self.assertEqual(
            status.available_mb,
            512,
        )
        self.assertEqual(
            status.used_percent,
            50.0,
        )
        self.assertEqual(
            status.state,
            "normal",
        )
        self.assertIsNone(status.error)

    def test_accepts_string_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=2048,
                available_kb=1024,
            )

            status = collect_memory_status(path=str(path))

        self.assertEqual(
            status.total_mb,
            2,
        )
        self.assertEqual(
            status.available_mb,
            1,
        )

    def test_default_path_constant(self) -> None:
        self.assertEqual(
            MEMINFO_PATH,
            Path("/proc/meminfo"),
        )

    def test_uses_default_meminfo_path(self) -> None:
        mock_file = unittest.mock.mock_open(
            read_data=("MemTotal: 1048576 kB\nMemAvailable: 524288 kB\n")
        )

        with patch.object(
            Path,
            "open",
            mock_file,
        ):
            status = collect_memory_status()

        mock_file.assert_called_once_with(
            "r",
            encoding="utf-8",
        )
        self.assertEqual(
            status.used_percent,
            50.0,
        )

    def test_ignores_unrelated_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1048576,
                available_kb=524288,
                extra=(
                    "MemFree:        100000 kB\n"
                    "Buffers:         50000 kB\n"
                    "Cached:         200000 kB\n"
                ),
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.used_percent,
            50.0,
        )

    def test_ignores_lines_without_separator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            path.write_text(
                ("invalid line\nMemTotal: 1048576 kB\nMemAvailable: 524288 kB\n"),
                encoding="utf-8",
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.used_percent,
            50.0,
        )

    def test_ignores_fields_without_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            path.write_text(
                ("Ignored:\nMemTotal: 1048576 kB\nMemAvailable: 524288 kB\n"),
                encoding="utf-8",
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.used_percent,
            50.0,
        )

    def test_strips_field_names_and_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            path.write_text(
                (" MemTotal :   1048576 kB\n MemAvailable : 524288 kB\n"),
                encoding="utf-8",
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.total_mb,
            1024,
        )
        self.assertEqual(
            status.available_mb,
            512,
        )

    def test_rounds_memory_values_to_mb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1536,
                available_kb=768,
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.total_mb,
            2,
        )
        self.assertEqual(
            status.available_mb,
            1,
        )

    def test_rounds_used_percent_to_one_decimal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=3000,
                available_kb=1000,
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.used_percent,
            66.7,
        )

    def test_classifies_normal_memory(self) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1000,
                available_kb=301,
            )

            status = collect_memory_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.state,
            "normal",
        )

    def test_classifies_high_memory_at_threshold(
        self,
    ) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1000,
                available_kb=300,
            )

            status = collect_memory_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.used_percent,
            70.0,
        )
        self.assertEqual(
            status.state,
            "high",
        )

    def test_classifies_memory_between_thresholds(
        self,
    ) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1000,
                available_kb=200,
            )

            status = collect_memory_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.state,
            "high",
        )

    def test_classifies_critical_memory_at_threshold(
        self,
    ) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1000,
                available_kb=100,
            )

            status = collect_memory_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.used_percent,
            90.0,
        )
        self.assertEqual(
            status.state,
            "critical",
        )

    def test_classifies_memory_above_critical(
        self,
    ) -> None:
        config = make_config(
            high_percent=70.0,
            critical_percent=90.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1000,
                available_kb=50,
            )

            status = collect_memory_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.state,
            "critical",
        )

    def test_supports_all_memory_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1024,
                available_kb=1024,
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.used_percent,
            0.0,
        )
        self.assertEqual(
            status.state,
            "normal",
        )

    def test_returns_unknown_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing"

            status = collect_memory_status(path=path)

        self.assertIsNone(status.total_mb)
        self.assertIsNone(status.available_mb)
        self.assertIsNone(status.used_percent)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIsNotNone(status.error)

    def test_returns_unknown_when_total_is_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            path.write_text(
                "MemAvailable: 512 kB\n",
                encoding="utf-8",
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIn(
            "MemTotal",
            status.error or "",
        )

    def test_returns_unknown_when_available_is_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            path.write_text(
                "MemTotal: 1024 kB\n",
                encoding="utf-8",
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIn(
            "MemAvailable",
            status.error or "",
        )

    def test_returns_unknown_for_invalid_numeric_value(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            path.write_text(
                ("MemTotal: invalid kB\nMemAvailable: 512 kB\n"),
                encoding="utf-8",
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIsNotNone(status.error)

    def test_returns_unknown_for_zero_total(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=0,
                available_kb=0,
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "MemTotal must be greater than 0",
        )

    def test_returns_unknown_for_negative_total(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=-1,
                available_kb=0,
            )

            status = collect_memory_status(path=path)

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "MemTotal must be greater than 0",
        )

    def test_returns_unknown_for_read_error(self) -> None:
        with patch.object(
            Path,
            "open",
            side_effect=OSError("permission denied"),
        ):
            status = collect_memory_status()

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "permission denied",
        )

    def test_rejects_invalid_config_before_opening_file(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "open",
            ) as open_file,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_memory_status(
                object(),  # type: ignore[arg-type]
            )

        open_file.assert_not_called()

    def test_rejects_invalid_path_before_opening_file(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "open",
            ) as open_file,
            self.assertRaisesRegex(
                TypeError,
                "path must be a string or Path",
            ),
        ):
            collect_memory_status(
                path=True,  # type: ignore[arg-type]
            )

        open_file.assert_not_called()

    def test_unexpected_threshold_error_propagates(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "meminfo"

            write_meminfo(
                path,
                total_kb=1024,
                available_kb=512,
            )

            with (
                patch(
                    f"{MODULE}.validate_config",
                    return_value=object(),
                ),
                self.assertRaises(
                    AttributeError,
                ),
            ):
                collect_memory_status(path=path)

    if __name__ == "__main__":
        unittest.main()
