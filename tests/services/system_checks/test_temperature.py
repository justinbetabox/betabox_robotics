from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.system_checks.temperature import (
    TEMPERATURE_PATH,
    collect_temperature_status,
)

MODULE = "betabox_robotics.services.system_checks.temperature"


def make_config(
    *,
    high_celsius: float,
    critical_celsius: float,
):
    temperature = replace(
        DEFAULT_PLATFORM_CONFIG.health.temperature,
        high_celsius=high_celsius,
        critical_celsius=critical_celsius,
    )
    health = replace(
        DEFAULT_PLATFORM_CONFIG.health,
        temperature=temperature,
    )

    return replace(
        DEFAULT_PLATFORM_CONFIG,
        health=health,
    )


class CollectTemperatureStatusTests(unittest.TestCase):
    def test_reads_temperature_from_supplied_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "42500\n",
                encoding="utf-8",
            )

            status = collect_temperature_status(path=path)

        self.assertEqual(
            status.celsius,
            42.5,
        )
        self.assertEqual(
            status.state,
            "normal",
        )
        self.assertIsNone(status.error)

    def test_accepts_string_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "50000",
                encoding="utf-8",
            )

            status = collect_temperature_status(path=str(path))

        self.assertEqual(
            status.celsius,
            50.0,
        )

    def test_uses_default_temperature_path(
        self,
    ) -> None:
        with patch.object(
            Path,
            "read_text",
            return_value="42000",
        ) as read_text:
            status = collect_temperature_status()

        read_text.assert_called_once_with(encoding="utf-8")
        self.assertEqual(
            status.celsius,
            42.0,
        )

    def test_default_path_constant(self) -> None:
        self.assertEqual(
            TEMPERATURE_PATH,
            Path("/sys/class/thermal/thermal_zone0/temp"),
        )

    def test_strips_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "  42500 \n",
                encoding="utf-8",
            )

            status = collect_temperature_status(path=path)

        self.assertEqual(
            status.celsius,
            42.5,
        )

    def test_classifies_normal_temperature(self) -> None:
        config = make_config(
            high_celsius=70.0,
            critical_celsius=80.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "69999",
                encoding="utf-8",
            )

            status = collect_temperature_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.state,
            "normal",
        )

    def test_classifies_high_temperature(self) -> None:
        config = make_config(
            high_celsius=70.0,
            critical_celsius=80.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "70000",
                encoding="utf-8",
            )

            status = collect_temperature_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.celsius,
            70.0,
        )
        self.assertEqual(
            status.state,
            "high",
        )

    def test_classifies_temperature_between_thresholds(
        self,
    ) -> None:
        config = make_config(
            high_celsius=70.0,
            critical_celsius=80.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "75000",
                encoding="utf-8",
            )

            status = collect_temperature_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.state,
            "high",
        )

    def test_classifies_critical_temperature(
        self,
    ) -> None:
        config = make_config(
            high_celsius=70.0,
            critical_celsius=80.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "80000",
                encoding="utf-8",
            )

            status = collect_temperature_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.celsius,
            80.0,
        )
        self.assertEqual(
            status.state,
            "critical",
        )

    def test_classifies_above_critical_temperature(
        self,
    ) -> None:
        config = make_config(
            high_celsius=70.0,
            critical_celsius=80.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "85000",
                encoding="utf-8",
            )

            status = collect_temperature_status(
                config,
                path=path,
            )

        self.assertEqual(
            status.state,
            "critical",
        )

    def test_supports_negative_temperature(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "-5000",
                encoding="utf-8",
            )

            status = collect_temperature_status(path=path)

        self.assertEqual(
            status.celsius,
            -5.0,
        )
        self.assertEqual(
            status.state,
            "normal",
        )

    def test_returns_unknown_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing"

            status = collect_temperature_status(path=path)

        self.assertIsNone(status.celsius)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIsNotNone(status.error)

    def test_returns_unknown_for_invalid_number(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "not-a-number",
                encoding="utf-8",
            )

            status = collect_temperature_status(path=path)

        self.assertIsNone(status.celsius)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIsNotNone(status.error)

    def test_returns_unknown_for_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "",
                encoding="utf-8",
            )

            status = collect_temperature_status(path=path)

        self.assertIsNone(status.celsius)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIsNotNone(status.error)

    def test_returns_unknown_for_read_error(self) -> None:
        with patch.object(
            Path,
            "read_text",
            side_effect=OSError("permission denied"),
        ):
            status = collect_temperature_status()

        self.assertIsNone(status.celsius)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "permission denied",
        )

    def test_rejects_invalid_config_before_path_read(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "read_text",
            ) as read_text,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_temperature_status(
                object(),  # type: ignore[arg-type]
            )

        read_text.assert_not_called()

    def test_rejects_invalid_path_before_read(self) -> None:
        with (
            patch.object(
                Path,
                "read_text",
            ) as read_text,
            self.assertRaisesRegex(
                TypeError,
                "path must be a string or Path",
            ),
        ):
            collect_temperature_status(
                path=True,  # type: ignore[arg-type]
            )

        read_text.assert_not_called()

    def test_unexpected_threshold_error_propagates(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "temp"
            path.write_text(
                "42500",
                encoding="utf-8",
            )

            with (
                patch(
                    f"{MODULE}.validate_config",
                    return_value=object(),
                ),
                self.assertRaises(AttributeError),
            ):
                collect_temperature_status(path=path)


if __name__ == "__main__":
    unittest.main()
