from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.verify_checks.launchpad import (
    check_launchpad,
)
from betabox_robotics.services.verify_checks.models import (
    CheckResult,
)

MODULE = "betabox_robotics.services.verify_checks.launchpad"


def make_result(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class CheckLaunchpadTests(unittest.TestCase):
    def test_reports_healthy_launchpad(self) -> None:
        config = DEFAULT_PLATFORM_CONFIG
        unit = config.services.launchpad.unit
        timeout = config.verification.command_timeout_seconds

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    stdout="active\n",
                ),
            ) as run,
            patch(
                f"{MODULE}.check_json_health",
                return_value=(
                    True,
                    "healthy",
                ),
            ) as check_health,
        ):
            result = check_launchpad(config)

        run.assert_called_once_with(
            [
                "systemctl",
                "is-active",
                unit,
            ],
            timeout=timeout,
        )
        check_health.assert_called_once_with(
            config.network.launchpad_health_url,
            expected_service="launchpad",
            timeout=float(timeout),
        )
        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=True,
                message="Launchpad responding",
            ),
        )

    def test_uses_default_config(self) -> None:
        config = DEFAULT_PLATFORM_CONFIG
        unit = config.services.launchpad.unit
        timeout = config.verification.command_timeout_seconds

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    stdout="active\n",
                ),
            ) as run,
            patch(
                f"{MODULE}.check_json_health",
                return_value=(
                    True,
                    "healthy",
                ),
            ) as check_health,
        ):
            result = check_launchpad()

        self.assertTrue(result.ok)
        run.assert_called_once_with(
            [
                "systemctl",
                "is-active",
                unit,
            ],
            timeout=timeout,
        )
        check_health.assert_called_once_with(
            config.network.launchpad_health_url,
            expected_service="launchpad",
            timeout=float(timeout),
        )

    def test_preserves_health_failure_message(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    stdout="active\n",
                ),
            ),
            patch(
                f"{MODULE}.check_json_health",
                return_value=(
                    False,
                    "unexpected service value",
                ),
            ),
        ):
            result = check_launchpad()

        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=False,
                message=("unexpected service value"),
            ),
        )

    def test_reports_unknown_when_command_cannot_run(
        self,
    ) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with (
            patch(
                f"{MODULE}.run",
                return_value=None,
            ),
            patch(f"{MODULE}.check_json_health") as check_health,
        ):
            result = check_launchpad()

        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=False,
                message=f"{unit} is unknown",
            ),
        )
        check_health.assert_not_called()

    def test_reports_inactive_service(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=3,
                    stdout="inactive\n",
                ),
            ),
            patch(f"{MODULE}.check_json_health") as check_health,
        ):
            result = check_launchpad()

        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=False,
                message=f"{unit} is inactive",
            ),
        )
        check_health.assert_not_called()

    def test_reports_failed_service(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=3,
                    stdout="failed\n",
                ),
            ),
            patch(f"{MODULE}.check_json_health") as check_health,
        ):
            result = check_launchpad()

        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=False,
                message=f"{unit} is failed",
            ),
        )
        check_health.assert_not_called()

    def test_failed_service_uses_stderr(
        self,
    ) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                    stderr="systemctl failed\n",
                ),
            ),
            patch(f"{MODULE}.check_json_health") as check_health,
        ):
            result = check_launchpad()

        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=False,
                message=(f"{unit} is systemctl failed"),
            ),
        )
        check_health.assert_not_called()

    def test_failed_service_without_output_is_unknown(
        self,
    ) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                ),
            ),
            patch(f"{MODULE}.check_json_health") as check_health,
        ):
            result = check_launchpad()

        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=False,
                message=f"{unit} is unknown",
            ),
        )
        check_health.assert_not_called()

    def test_active_state_with_nonzero_code_fails(
        self,
    ) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                    stdout="active\n",
                ),
            ),
            patch(f"{MODULE}.check_json_health") as check_health,
        ):
            result = check_launchpad()

        self.assertEqual(
            result,
            CheckResult(
                name="launchpad:http",
                ok=False,
                message=f"{unit} is active",
            ),
        )
        check_health.assert_not_called()

    def test_rejects_invalid_config_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            patch(f"{MODULE}.check_json_health") as check_health,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            check_launchpad(
                object()  # type: ignore[arg-type]
            )

        run.assert_not_called()
        check_health.assert_not_called()

    def test_unexpected_command_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.run",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_launchpad()

        self.assertIs(
            context.exception,
            error,
        )

    def test_unexpected_health_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    stdout="active\n",
                ),
            ),
            patch(
                f"{MODULE}.check_json_health",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_launchpad()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
