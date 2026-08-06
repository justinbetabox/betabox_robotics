from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.hardware_checks.audio import (
    _validate_config,
    collect_audio_status,
)

MODULE = "betabox_robotics.services.hardware_checks.audio"


class ValidateConfigTests(unittest.TestCase):
    def test_accepts_platform_config(self) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_rejects_invalid_config(self) -> None:
        for value in (
            None,
            object(),
            "config",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "config must be a PlatformConfig",
                ),
            ):
                _validate_config(value)


class CollectAudioStatusTests(unittest.TestCase):
    def test_runs_aplay_with_configured_timeout(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=0,
            stdout="no matching audio device",
            stderr="",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ) as run:
            status = collect_audio_status()

        run.assert_called_once_with(
            [
                "aplay",
                "-l",
            ],
            timeout=(DEFAULT_PLATFORM_CONFIG.verification.command_timeout_seconds),
        )

        self.assertFalse(status.available)

    def test_returns_unavailable_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            status = collect_audio_status()

        self.assertFalse(status.available)
        self.assertIsNone(status.device)
        self.assertEqual(
            status.error,
            "could not run aplay",
        )

    def test_returns_command_output_for_failure(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=1,
            stdout="",
            stderr=" permission denied \n",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertFalse(status.available)
        self.assertIsNone(status.device)
        self.assertEqual(
            status.error,
            "permission denied",
        )

    def test_combines_stdout_and_stderr_for_failure(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=1,
            stdout="audio error: ",
            stderr="device busy",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertEqual(
            status.error,
            "audio error: device busy",
        )

    def test_uses_fallback_for_failure_without_output(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=1,
            stdout=" ",
            stderr=" ",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertFalse(status.available)
        self.assertEqual(
            status.error,
            "aplay failed",
        )

    def test_detects_hifiberry_identifier_in_stdout(
        self,
    ) -> None:
        identifier = DEFAULT_PLATFORM_CONFIG.verification.hifiberry_identifiers[0]

        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=0,
            stdout=(
                f"**** List of PLAYBACK Hardware Devices ****\ncard 0: {identifier}\n"
            ),
            stderr="",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertTrue(status.available)
        self.assertEqual(
            status.device,
            "HifiBerry DAC",
        )
        self.assertIsNone(status.error)

    def test_detects_hifiberry_identifier_in_stderr(
        self,
    ) -> None:
        identifier = DEFAULT_PLATFORM_CONFIG.verification.hifiberry_identifiers[0]

        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=0,
            stdout="",
            stderr=f"device: {identifier}",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertTrue(status.available)
        self.assertEqual(
            status.device,
            "HifiBerry DAC",
        )

    def test_detects_any_configured_identifier(self) -> None:
        identifiers = DEFAULT_PLATFORM_CONFIG.verification.hifiberry_identifiers

        for identifier in identifiers:
            completed = subprocess.CompletedProcess(
                args=[
                    "aplay",
                    "-l",
                ],
                returncode=0,
                stdout=f"card: {identifier}",
                stderr="",
            )

            with (
                self.subTest(identifier=identifier),
                patch(
                    f"{MODULE}.run",
                    return_value=completed,
                ),
            ):
                status = collect_audio_status()

            self.assertTrue(status.available)
            self.assertEqual(
                status.device,
                "HifiBerry DAC",
            )

    def test_returns_unavailable_when_device_not_detected(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=0,
            stdout=("card 0: Headphones [bcm2835 Headphones]"),
            stderr="",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertFalse(status.available)
        self.assertIsNone(status.device)
        self.assertEqual(
            status.error,
            ("HifiBerry audio device was not detected"),
        )

    def test_empty_successful_output_means_not_detected(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertFalse(status.available)
        self.assertEqual(
            status.error,
            ("HifiBerry audio device was not detected"),
        )

    def test_matching_is_case_sensitive(self) -> None:
        identifier = DEFAULT_PLATFORM_CONFIG.verification.hifiberry_identifiers[0]

        completed = subprocess.CompletedProcess(
            args=[
                "aplay",
                "-l",
            ],
            returncode=0,
            stdout=identifier.swapcase(),
            stderr="",
        )

        with patch(
            f"{MODULE}.run",
            return_value=completed,
        ):
            status = collect_audio_status()

        self.assertFalse(status.available)

    def test_rejects_invalid_config_before_running_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_audio_status(
                object()  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_unexpected_run_error_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.run",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_audio_status()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
