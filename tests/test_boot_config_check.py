import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from betabox_robotics.config import DEFAULT_PLATFORM_CONFIG
from betabox_robotics.services.install_checks.software import (
    check_config_line,
)


class TestBootConfigCheck(unittest.TestCase):
    def test_active_configuration_required(self):
        cases = {
            "#dtparam=i2c_arm=on\n": False,
            "  # dtparam=i2c_arm=on\n": False,
            "dtparam=i2c_arm=on\n": True,
            "  dtparam=i2c_arm=on # enabled\n": True,
            "dtparam=i2c_arm=off\n": False,
            "dtparam=i2c_arm=on_extra\n": False,
            "": False,
            "[none]\ndtparam=i2c_arm=on\n": False,
            "[cm5]\ndtparam=i2c_arm=on\n": False,
            "[cm5]\ndtparam=i2c_arm=on\n[all]\n": False,
            "[cm5]\ndtparam=i2c_arm=on\n[all]\ndtparam=i2c_arm=on\n": True,
        }

        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.txt"

            config = replace(
                DEFAULT_PLATFORM_CONFIG,
                verification=replace(
                    DEFAULT_PLATFORM_CONFIG.verification,
                    boot_config_file=path,
                ),
            )

            for content, expected in cases.items():
                with self.subTest(content=content):
                    path.write_text(content)

                    result = check_config_line(
                        "dtparam=i2c_arm=on",
                        config,
                    )

                    self.assertEqual(result.ok, expected)


if __name__ == "__main__":
    unittest.main()
