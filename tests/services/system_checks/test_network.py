from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from betabox_robotics.services.system_checks.network import (
    collect_network_interface,
)

MODULE = "betabox_robotics.services.system_checks.network"


def make_result(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[
            "nmcli",
            "-t",
            "-f",
            "GENERAL.STATE,GENERAL.CONNECTION",
            "device",
            "show",
            "wlan0",
        ],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class CollectNetworkInterfaceTests(unittest.TestCase):
    def test_runs_nmcli_for_interface(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("GENERAL.STATE:100 (connected)\nGENERAL.CONNECTION:Betabox\n")
            ),
        ) as run:
            status = collect_network_interface(" wlan0 ")

        run.assert_called_once_with(
            [
                "nmcli",
                "-t",
                "-f",
                ("GENERAL.STATE,GENERAL.CONNECTION"),
                "device",
                "show",
                "wlan0",
            ],
            timeout=5,
        )

        self.assertEqual(
            status.name,
            "wlan0",
        )
        self.assertTrue(status.available)
        self.assertTrue(status.connected)
        self.assertEqual(
            status.state,
            "100 (connected)",
        )
        self.assertEqual(
            status.connection,
            "Betabox",
        )
        self.assertIsNone(status.error)

    def test_reports_connected_interface(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=(
                    "GENERAL.STATE:"
                    "100 (connected)\n"
                    "GENERAL.CONNECTION:"
                    "Wired connection 1\n"
                )
            ),
        ):
            status = collect_network_interface("eth0")

        self.assertTrue(status.available)
        self.assertTrue(status.connected)
        self.assertEqual(
            status.state,
            "100 (connected)",
        )
        self.assertEqual(
            status.connection,
            "Wired connection 1",
        )

    def test_reports_disconnected_interface(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("GENERAL.STATE:30 (disconnected)\nGENERAL.CONNECTION:--\n")
            ),
        ):
            status = collect_network_interface("eth0")

        self.assertTrue(status.available)
        self.assertFalse(status.connected)
        self.assertEqual(
            status.state,
            "30 (disconnected)",
        )
        self.assertIsNone(status.connection)
        self.assertIsNone(status.error)

    def test_empty_connection_becomes_none(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("GENERAL.STATE:30 (disconnected)\nGENERAL.CONNECTION:\n")
            ),
        ):
            status = collect_network_interface("eth0")

        self.assertIsNone(status.connection)

    def test_missing_connection_stays_none(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=("GENERAL.STATE:100 (connected)\n")),
        ):
            status = collect_network_interface("wlan0")

        self.assertTrue(status.connected)
        self.assertIsNone(status.connection)

    def test_missing_state_uses_unknown(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(stdout=("GENERAL.CONNECTION:Betabox\n")),
        ):
            status = collect_network_interface("wlan0")

        self.assertTrue(status.available)
        self.assertFalse(status.connected)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.connection,
            "Betabox",
        )

    def test_empty_state_uses_unknown(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("GENERAL.STATE:\nGENERAL.CONNECTION:Betabox\n")
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertFalse(status.connected)

    def test_ignores_unrelated_fields(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=(
                    "GENERAL.DEVICE:wlan0\n"
                    "GENERAL.TYPE:wifi\n"
                    "GENERAL.STATE:"
                    "100 (connected)\n"
                    "GENERAL.CONNECTION:"
                    "Betabox\n"
                )
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertTrue(status.connected)
        self.assertEqual(
            status.connection,
            "Betabox",
        )

    def test_ignores_lines_without_separator(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=(
                    "invalid line\n"
                    "GENERAL.STATE:"
                    "100 (connected)\n"
                    "GENERAL.CONNECTION:"
                    "Betabox\n"
                )
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertTrue(status.connected)
        self.assertEqual(
            status.connection,
            "Betabox",
        )

    def test_splits_only_first_separator(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=(
                    "GENERAL.STATE:100 (connected)\nGENERAL.CONNECTION:Office:Lab\n"
                )
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertEqual(
            status.connection,
            "Office:Lab",
        )

    def test_strips_keys_and_values(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=(
                    " GENERAL.STATE : "
                    "100 (connected) \n"
                    " GENERAL.CONNECTION : "
                    "Betabox \n"
                )
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertTrue(status.connected)
        self.assertEqual(
            status.connection,
            "Betabox",
        )

    def test_connected_requires_state_prefix_100(
        self,
    ) -> None:
        for state in (
            "100",
            "100 (connected)",
            "100-custom",
        ):
            with (
                self.subTest(state=state),
                patch(
                    f"{MODULE}.run",
                    return_value=make_result(stdout=(f"GENERAL.STATE:{state}\n")),
                ),
            ):
                status = collect_network_interface("wlan0")

            self.assertTrue(status.connected)

    def test_non_connected_states_are_false(
        self,
    ) -> None:
        for state in (
            "20 (unavailable)",
            "30 (disconnected)",
            "40 (connecting)",
            "unknown",
        ):
            with (
                self.subTest(state=state),
                patch(
                    f"{MODULE}.run",
                    return_value=make_result(stdout=(f"GENERAL.STATE:{state}\n")),
                ),
            ):
                status = collect_network_interface("wlan0")

            self.assertFalse(status.connected)

    def test_returns_unavailable_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            status = collect_network_interface("wlan0")

        self.assertEqual(
            status.name,
            "wlan0",
        )
        self.assertFalse(status.available)
        self.assertFalse(status.connected)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertIsNone(status.connection)
        self.assertEqual(
            status.error,
            "nmcli device query failed",
        )

    def test_returns_stderr_for_failed_command(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=10,
                stderr=" device not found \n",
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertFalse(status.available)
        self.assertEqual(
            status.error,
            "device not found",
        )

    def test_uses_stdout_when_failed_without_stderr(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=10,
                stdout=" unknown device \n",
                stderr="",
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertEqual(
            status.error,
            "unknown device",
        )

    def test_uses_fallback_when_failed_without_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=10,
                stdout=" ",
                stderr=" ",
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertEqual(
            status.error,
            "nmcli device query failed",
        )

    def test_stderr_takes_precedence_over_stdout(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=10,
                stdout="stdout message",
                stderr="stderr message",
            ),
        ):
            status = collect_network_interface("wlan0")

        self.assertEqual(
            status.error,
            "stderr message",
        )

    def test_rejects_invalid_name_before_command(
        self,
    ) -> None:
        for value in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                patch(f"{MODULE}.run") as run,
                self.assertRaisesRegex(
                    TypeError,
                    "name must be a string",
                ),
            ):
                collect_network_interface(
                    value  # type: ignore[arg-type]
                )

            run.assert_not_called()

    def test_rejects_empty_name_before_command(
        self,
    ) -> None:
        for value in (
            "",
            " ",
            "\t",
        ):
            with (
                self.subTest(value=value),
                patch(f"{MODULE}.run") as run,
                self.assertRaisesRegex(
                    ValueError,
                    "name cannot be empty",
                ),
            ):
                collect_network_interface(value)

            run.assert_not_called()

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
            collect_network_interface("wlan0")

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
