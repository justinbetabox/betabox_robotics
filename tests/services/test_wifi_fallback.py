from __future__ import annotations

import argparse
import subprocess
import unittest
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.wifi_fallback import (
    _validate_config,
    _validate_flag,
    _validate_non_negative_int,
    _validate_positive_float,
    _validate_string,
    ap_connection_exists,
    command_error,
    dynamic_ssid,
    enable_wifi_radio,
    ethernet_connected,
    main,
    nmcli_available,
    parse_args,
    run_wifi_fallback,
    set_ap_ssid,
    start_ap,
    wait_for_wifi_ip,
    wifi_has_ip,
    wifi_radio_enabled,
)

MODULE = "betabox_robotics.services.wifi_fallback"


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


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_config(
        self,
    ) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_validate_config_rejects_invalid_value(
        self,
    ) -> None:
        for value in (
            None,
            object(),
            "config",
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("config must be a PlatformConfig"),
                ),
            ):
                _validate_config(value)

    def test_validate_string_strips_value(
        self,
    ) -> None:
        result = _validate_string(
            " wlan0 ",
            name="iface",
        )

        self.assertEqual(
            result,
            "wlan0",
        )

    def test_validate_string_rejects_invalid_type(
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
                self.assertRaisesRegex(
                    TypeError,
                    "iface must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="iface",
                )

    def test_validate_string_rejects_empty_value(
        self,
    ) -> None:
        for value in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "iface cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="iface",
                )

    def test_validate_non_negative_int_accepts_zero(
        self,
    ) -> None:
        self.assertEqual(
            _validate_non_negative_int(
                0,
                name="delay_seconds",
            ),
            0,
        )

    def test_validate_non_negative_int_accepts_positive(
        self,
    ) -> None:
        self.assertEqual(
            _validate_non_negative_int(
                30,
                name="delay_seconds",
            ),
            30,
        )

    def test_validate_non_negative_int_rejects_boolean(
        self,
    ) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("delay_seconds must be an integer"),
                ),
            ):
                _validate_non_negative_int(
                    value,
                    name="delay_seconds",
                )

    def test_validate_non_negative_int_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            None,
            1.5,
            "5",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("delay_seconds must be an integer"),
                ),
            ):
                _validate_non_negative_int(
                    value,
                    name="delay_seconds",
                )

    def test_validate_non_negative_int_rejects_negative(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("delay_seconds cannot be negative"),
        ):
            _validate_non_negative_int(
                -1,
                name="delay_seconds",
            )

    def test_validate_positive_float_accepts_integer(
        self,
    ) -> None:
        self.assertEqual(
            _validate_positive_float(
                1,
                name="poll_interval",
            ),
            1.0,
        )

    def test_validate_positive_float_accepts_float(
        self,
    ) -> None:
        self.assertEqual(
            _validate_positive_float(
                0.5,
                name="poll_interval",
            ),
            0.5,
        )

    def test_validate_positive_float_rejects_boolean(
        self,
    ) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("poll_interval must be a number"),
                ),
            ):
                _validate_positive_float(
                    value,
                    name="poll_interval",
                )

    def test_validate_positive_float_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            None,
            "0.5",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("poll_interval must be a number"),
                ),
            ):
                _validate_positive_float(
                    value,
                    name="poll_interval",
                )

    def test_validate_positive_float_rejects_non_positive(
        self,
    ) -> None:
        for value in (
            0,
            0.0,
            -0.5,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("poll_interval must be greater than 0"),
                ),
            ):
                _validate_positive_float(
                    value,
                    name="poll_interval",
                )

    def test_validate_flag_accepts_boolean(
        self,
    ) -> None:
        self.assertTrue(
            _validate_flag(
                True,
                name="dry_run",
            )
        )
        self.assertFalse(
            _validate_flag(
                False,
                name="dry_run",
            )
        )

    def test_validate_flag_rejects_non_boolean(
        self,
    ) -> None:
        for value in (
            None,
            0,
            1,
            "true",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("dry_run must be a boolean"),
                ),
            ):
                _validate_flag(
                    value,
                    name="dry_run",
                )


class WaitForWifiIpTests(unittest.TestCase):
    def test_returns_true_immediately_when_wifi_has_ip(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.time.monotonic",
                side_effect=(
                    10.0,
                    10.1,
                ),
            ),
            patch(
                f"{MODULE}.wifi_has_ip",
                return_value=True,
            ) as wifi_has_ip,
            patch(f"{MODULE}.time.sleep") as sleep,
        ):
            result = wait_for_wifi_ip(
                " wlan0 ",
                timeout_seconds=5,
                poll_interval=0.5,
            )

        self.assertTrue(result)
        wifi_has_ip.assert_called_once_with("wlan0")
        sleep.assert_not_called()

    def test_polls_until_wifi_gets_ip(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.time.monotonic",
                side_effect=(
                    10.0,
                    10.1,
                    10.6,
                ),
            ),
            patch(
                f"{MODULE}.wifi_has_ip",
                side_effect=(
                    False,
                    True,
                ),
            ) as wifi_has_ip,
            patch(f"{MODULE}.time.sleep") as sleep,
        ):
            result = wait_for_wifi_ip(
                "wlan0",
                timeout_seconds=5,
                poll_interval=0.5,
            )

        self.assertTrue(result)
        self.assertEqual(
            wifi_has_ip.call_args_list,
            [
                call("wlan0"),
                call("wlan0"),
            ],
        )
        sleep.assert_called_once_with(0.5)

    def test_performs_final_check_after_timeout(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.time.monotonic",
                side_effect=(
                    10.0,
                    15.0,
                ),
            ),
            patch(
                f"{MODULE}.wifi_has_ip",
                return_value=True,
            ) as wifi_has_ip,
            patch(f"{MODULE}.time.sleep") as sleep,
        ):
            result = wait_for_wifi_ip(
                "wlan0",
                timeout_seconds=5,
            )

        self.assertTrue(result)
        wifi_has_ip.assert_called_once_with("wlan0")
        sleep.assert_not_called()

    def test_returns_false_after_timeout(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.time.monotonic",
                side_effect=(
                    10.0,
                    15.0,
                ),
            ),
            patch(
                f"{MODULE}.wifi_has_ip",
                return_value=False,
            ) as wifi_has_ip,
            patch(f"{MODULE}.time.sleep") as sleep,
        ):
            result = wait_for_wifi_ip(
                "wlan0",
                timeout_seconds=5,
            )

        self.assertFalse(result)
        wifi_has_ip.assert_called_once_with("wlan0")
        sleep.assert_not_called()

    def test_zero_timeout_performs_one_check(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.time.monotonic",
                side_effect=(
                    10.0,
                    10.0,
                ),
            ),
            patch(
                f"{MODULE}.wifi_has_ip",
                return_value=False,
            ) as wifi_has_ip,
            patch(f"{MODULE}.time.sleep") as sleep,
        ):
            result = wait_for_wifi_ip(
                "wlan0",
                timeout_seconds=0,
            )

        self.assertFalse(result)
        wifi_has_ip.assert_called_once_with("wlan0")
        sleep.assert_not_called()

    def test_rejects_invalid_iface_before_clock(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.time.monotonic") as monotonic,
            self.assertRaisesRegex(
                TypeError,
                "iface must be a string",
            ),
        ):
            wait_for_wifi_ip(
                None,  # type: ignore[arg-type]
            )

        monotonic.assert_not_called()

    def test_rejects_negative_timeout_before_clock(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.time.monotonic") as monotonic,
            self.assertRaisesRegex(
                ValueError,
                ("timeout_seconds cannot be negative"),
            ),
        ):
            wait_for_wifi_ip(
                "wlan0",
                timeout_seconds=-1,
            )

        monotonic.assert_not_called()

    def test_rejects_invalid_poll_interval_before_clock(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.time.monotonic") as monotonic,
            self.assertRaisesRegex(
                ValueError,
                ("poll_interval must be greater than 0"),
            ),
        ):
            wait_for_wifi_ip(
                "wlan0",
                poll_interval=0,
            )

        monotonic.assert_not_called()


class DynamicSsidTests(unittest.TestCase):
    def test_returns_identity_name(self) -> None:
        with patch(
            f"{MODULE}.identity_name",
            return_value="Betabox-7eea",
        ) as identity_name:
            result = dynamic_ssid(" Betabox ")

        identity_name.assert_called_once_with(
            "Betabox",
            fallback="UNKNOWN",
        )
        self.assertEqual(
            result,
            "Betabox-7eea",
        )

    def test_rejects_missing_identity_name(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.identity_name",
                return_value=None,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                ("failed to construct fallback SSID"),
            ),
        ):
            dynamic_ssid("Betabox")

    def test_rejects_empty_identity_name(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.identity_name",
                return_value=" ",
            ),
            self.assertRaisesRegex(
                ValueError,
                "ssid cannot be empty",
            ),
        ):
            dynamic_ssid("Betabox")

    def test_rejects_invalid_prefix_before_identity(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.identity_name") as identity_name,
            self.assertRaisesRegex(
                TypeError,
                "prefix must be a string",
            ),
        ):
            dynamic_ssid(
                None  # type: ignore[arg-type]
            )

        identity_name.assert_not_called()


class NmcliAvailableTests(unittest.TestCase):
    def test_returns_true_when_nmcli_exists(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(),
        ) as run:
            result = nmcli_available()

        self.assertTrue(result)
        run.assert_called_once_with(
            [
                "which",
                "nmcli",
            ],
            timeout=3,
        )

    def test_returns_false_for_nonzero_result(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(returncode=1),
        ):
            result = nmcli_available()

        self.assertFalse(result)

    def test_returns_false_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = nmcli_available()

        self.assertFalse(result)


class CommandErrorTests(unittest.TestCase):
    def test_none_result(self) -> None:
        self.assertEqual(
            command_error(None),
            "command could not be executed",
        )

    def test_uses_stderr_first(self) -> None:
        result = make_result(
            returncode=1,
            stdout="stdout\n",
            stderr="stderr\n",
        )

        self.assertEqual(
            command_error(result),
            "stderr",
        )

    def test_uses_stdout_when_stderr_empty(
        self,
    ) -> None:
        result = make_result(
            returncode=1,
            stdout="stdout\n",
        )

        self.assertEqual(
            command_error(result),
            "stdout",
        )

    def test_uses_returncode_fallback(
        self,
    ) -> None:
        result = make_result(returncode=7)

        self.assertEqual(
            command_error(result),
            "command exited with status 7",
        )

    def test_rejects_invalid_result(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("result must be a CompletedProcess or None"),
        ):
            command_error(
                object()  # type: ignore[arg-type]
            )


class WifiRadioEnabledTests(unittest.TestCase):
    def test_returns_true_when_enabled(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="enabled\n",
            ),
        ) as run:
            result = wifi_radio_enabled()

        self.assertTrue(result)
        run.assert_called_once_with(
            [
                "nmcli",
                "-t",
                "-f",
                "WIFI",
                "general",
            ],
            timeout=5,
        )

    def test_returns_false_when_disabled(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="disabled\n",
            ),
        ):
            result = wifi_radio_enabled()

        self.assertFalse(result)

    def test_returns_false_for_nonzero_result(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="enabled\n",
            ),
        ):
            result = wifi_radio_enabled()

        self.assertFalse(result)

    def test_returns_false_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = wifi_radio_enabled()

        self.assertFalse(result)


class EnableWifiRadioTests(unittest.TestCase):
    def test_returns_true_when_already_enabled(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.wifi_radio_enabled",
                return_value=True,
            ) as enabled,
            patch(f"{MODULE}.run") as run,
            patch("builtins.print") as print_message,
        ):
            result = enable_wifi_radio()

        self.assertTrue(result)
        enabled.assert_called_once_with()
        run.assert_not_called()
        print_message.assert_not_called()

    def test_dry_run_reports_actions(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.wifi_radio_enabled",
                return_value=False,
            ),
            patch(f"{MODULE}.run") as run,
            patch("builtins.print") as print_message,
        ):
            result = enable_wifi_radio(dry_run=True)

        self.assertTrue(result)
        run.assert_not_called()
        self.assertEqual(
            print_message.call_args_list,
            [
                call("wifi-fallback: Wi-Fi radio is disabled, enabling it"),
                call("wifi-fallback: would unblock and enable Wi-Fi"),
            ],
        )

    def test_enables_wifi_radio(self) -> None:
        with (
            patch(
                f"{MODULE}.wifi_radio_enabled",
                side_effect=(
                    False,
                    True,
                ),
            ),
            patch(
                f"{MODULE}.run",
                side_effect=(
                    make_result(),
                    make_result(),
                ),
            ) as run,
            patch("builtins.print") as print_message,
        ):
            result = enable_wifi_radio()

        self.assertTrue(result)
        self.assertEqual(
            run.call_args_list,
            [
                call(
                    [
                        "rfkill",
                        "unblock",
                        "wifi",
                    ],
                    timeout=5,
                ),
                call(
                    [
                        "nmcli",
                        "radio",
                        "wifi",
                        "on",
                    ],
                    timeout=10,
                ),
            ],
        )
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: Wi-Fi radio was disabled; successfully re-enabled"),
        )

    def test_rfkill_failure_is_warning_only(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.wifi_radio_enabled",
                side_effect=(
                    False,
                    True,
                ),
            ),
            patch(
                f"{MODULE}.run",
                side_effect=(
                    make_result(
                        returncode=1,
                        stderr="rfkill failed\n",
                    ),
                    make_result(),
                ),
            ),
            patch("builtins.print") as print_message,
        ):
            result = enable_wifi_radio()

        self.assertTrue(result)
        self.assertIn(
            call("wifi-fallback: rfkill unblock failed: rfkill failed"),
            print_message.call_args_list,
        )

    def test_enable_command_cannot_run(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.wifi_radio_enabled",
                return_value=False,
            ),
            patch(
                f"{MODULE}.run",
                side_effect=(
                    make_result(),
                    None,
                ),
            ),
            patch("builtins.print") as print_message,
        ):
            result = enable_wifi_radio()

        self.assertFalse(result)
        self.assertEqual(
            print_message.call_args_list[-1],
            call(
                "wifi-fallback: failed to enable "
                "Wi-Fi radio: command could not "
                "be executed"
            ),
        )

    def test_enable_command_failure(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.wifi_radio_enabled",
                return_value=False,
            ),
            patch(
                f"{MODULE}.run",
                side_effect=(
                    make_result(),
                    make_result(
                        returncode=1,
                        stderr="enable failed\n",
                    ),
                ),
            ),
            patch("builtins.print") as print_message,
        ):
            result = enable_wifi_radio()

        self.assertFalse(result)
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: failed to enable Wi-Fi radio: enable failed"),
        )

    def test_reports_radio_still_disabled(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.wifi_radio_enabled",
                side_effect=(
                    False,
                    False,
                ),
            ),
            patch(
                f"{MODULE}.run",
                side_effect=(
                    make_result(),
                    make_result(),
                ),
            ),
            patch("builtins.print") as print_message,
        ):
            result = enable_wifi_radio()

        self.assertFalse(result)
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: Wi-Fi radio remains disabled"),
        )

    def test_rejects_invalid_dry_run_before_probe(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.wifi_radio_enabled") as enabled,
            self.assertRaisesRegex(
                TypeError,
                ("dry_run must be a boolean"),
            ),
        ):
            enable_wifi_radio(
                dry_run=1  # type: ignore[arg-type]
            )

        enabled.assert_not_called()


class ConnectionProbeTests(unittest.TestCase):
    def test_ethernet_connected(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="100 (connected)\n",
            ),
        ) as run:
            result = ethernet_connected(" eth0 ")

        self.assertTrue(result)
        run.assert_called_once_with(
            [
                "nmcli",
                "-g",
                "GENERAL.STATE",
                "device",
                "show",
                "eth0",
            ],
            timeout=5,
        )

    def test_ethernet_not_connected(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="30 (disconnected)\n",
            ),
        ):
            result = ethernet_connected("eth0")

        self.assertFalse(result)

    def test_ethernet_command_failure(self) -> None:
        for result_value in (
            None,
            make_result(returncode=1),
        ):
            with (
                self.subTest(result=result_value),
                patch(
                    f"{MODULE}.run",
                    return_value=result_value,
                ),
            ):
                self.assertFalse(ethernet_connected("eth0"))

    def test_wifi_has_ip(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="192.168.1.10/24\n",
            ),
        ) as run:
            result = wifi_has_ip(" wlan0 ")

        self.assertTrue(result)
        run.assert_called_once_with(
            [
                "nmcli",
                "-g",
                "IP4.ADDRESS",
                "device",
                "show",
                "wlan0",
            ],
            timeout=5,
        )

    def test_wifi_without_ip(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(),
        ):
            result = wifi_has_ip("wlan0")

        self.assertFalse(result)

    def test_wifi_command_failure(self) -> None:
        for result_value in (
            None,
            make_result(
                returncode=1,
                stdout="192.168.1.10/24\n",
            ),
        ):
            with (
                self.subTest(result=result_value),
                patch(
                    f"{MODULE}.run",
                    return_value=result_value,
                ),
            ):
                self.assertFalse(wifi_has_ip("wlan0"))

    def test_ap_connection_exists(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("Home WiFi\nPiAP\n"),
            ),
        ) as run:
            result = ap_connection_exists(" PiAP ")

        self.assertTrue(result)
        run.assert_called_once_with(
            [
                "nmcli",
                "-t",
                "-f",
                "NAME",
                "connection",
                "show",
            ],
            timeout=5,
        )

    def test_ap_connection_missing(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="Home WiFi\n",
            ),
        ):
            result = ap_connection_exists("PiAP")

        self.assertFalse(result)

    def test_ap_connection_command_failure(
        self,
    ) -> None:
        for result_value in (
            None,
            make_result(returncode=1),
        ):
            with (
                self.subTest(result=result_value),
                patch(
                    f"{MODULE}.run",
                    return_value=result_value,
                ),
            ):
                self.assertFalse(ap_connection_exists("PiAP"))


class SetApSsidTests(unittest.TestCase):
    def test_dry_run(self) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            patch("builtins.print") as print_message,
        ):
            result = set_ap_ssid(
                " PiAP ",
                " Betabox-7eea ",
                dry_run=True,
            )

        self.assertTrue(result)
        run.assert_not_called()
        self.assertEqual(
            print_message.call_args_list,
            [
                call("wifi-fallback: using SSID: Betabox-7eea"),
                call("wifi-fallback: would set PiAP SSID to Betabox-7eea"),
            ],
        )

    def test_sets_ssid(self) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(),
            ) as run,
            patch("builtins.print"),
        ):
            result = set_ap_ssid(
                "PiAP",
                "Betabox-7eea",
            )

        self.assertTrue(result)
        run.assert_called_once_with(
            [
                "nmcli",
                "connection",
                "modify",
                "PiAP",
                "802-11-wireless.ssid",
                "Betabox-7eea",
            ],
            timeout=10,
        )

    def test_reports_failure(self) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(
                    returncode=1,
                    stderr="modify failed\n",
                ),
            ),
            patch("builtins.print") as print_message,
        ):
            result = set_ap_ssid(
                "PiAP",
                "Betabox-7eea",
            )

        self.assertFalse(result)
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: failed to set AP SSID: modify failed"),
        )

    def test_rejects_invalid_inputs_before_output(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                ValueError,
                "ap_name cannot be empty",
            ),
        ):
            set_ap_ssid(
                " ",
                "Betabox-7eea",
            )

        print_message.assert_not_called()


class StartApTests(unittest.TestCase):
    def test_dry_run(self) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            patch("builtins.print") as print_message,
        ):
            result = start_ap(
                " PiAP ",
                dry_run=True,
            )

        self.assertTrue(result)
        run.assert_not_called()
        self.assertEqual(
            print_message.call_args_list,
            [
                call("wifi-fallback: bringing up AP connection: PiAP"),
                call("wifi-fallback: would run nmcli connection up PiAP"),
            ],
        )

    def test_starts_ap(self) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=make_result(),
            ) as run,
            patch("builtins.print"),
        ):
            result = start_ap("PiAP")

        self.assertTrue(result)
        run.assert_called_once_with(
            [
                "nmcli",
                "connection",
                "up",
                "PiAP",
            ],
            timeout=30,
        )

    def test_reports_failure(self) -> None:
        with (
            patch(
                f"{MODULE}.run",
                return_value=None,
            ),
            patch("builtins.print") as print_message,
        ):
            result = start_ap("PiAP")

        self.assertFalse(result)
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: AP activation failed: command could not be executed"),
        )


class RunWifiFallbackTests(unittest.TestCase):
    def test_exits_when_nmcli_unavailable(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=False,
            ),
            patch(f"{MODULE}.time.sleep") as sleep,
            patch(f"{MODULE}.ethernet_connected") as ethernet,
            patch("builtins.print") as print_message,
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
            )

        self.assertEqual(result, 1)
        sleep.assert_not_called()
        ethernet.assert_not_called()
        self.assertEqual(
            print_message.call_args_list,
            [
                call("wifi-fallback: starting delay=0s"),
                call("wifi-fallback: nmcli not available"),
            ],
        )

    def test_sleeps_before_checks(self) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(f"{MODULE}.time.sleep") as sleep,
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=True,
            ) as ethernet,
            patch("builtins.print"),
        ):
            result = run_wifi_fallback(
                delay_seconds=3,
            )

        self.assertEqual(result, 0)
        sleep.assert_called_once_with(3)
        ethernet.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG.network.ethernet_interface
        )

    def test_dry_run_does_not_sleep(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(f"{MODULE}.time.sleep") as sleep,
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=True,
            ),
            patch("builtins.print") as print_message,
        ):
            result = run_wifi_fallback(
                delay_seconds=3,
                dry_run=True,
            )

        self.assertEqual(result, 0)
        sleep.assert_not_called()
        self.assertIn(
            call("wifi-fallback: would wait 3s"),
            print_message.call_args_list,
        )

    def test_exits_when_ethernet_connected(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=True,
            ) as ethernet,
            patch(f"{MODULE}.enable_wifi_radio") as enable_radio,
            patch("builtins.print") as print_message,
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
                eth_iface=" eth9 ",
            )

        self.assertEqual(result, 0)
        ethernet.assert_called_once_with("eth9")
        enable_radio.assert_not_called()
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: ethernet connected, exiting"),
        )

    def test_returns_one_when_radio_enable_fails(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=False,
            ),
            patch(
                f"{MODULE}.enable_wifi_radio",
                return_value=False,
            ) as enable_radio,
            patch(f"{MODULE}.wait_for_wifi_ip") as wait_for_ip,
            patch("builtins.print"),
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
                dry_run=True,
            )

        self.assertEqual(result, 1)
        enable_radio.assert_called_once_with(dry_run=True)
        wait_for_ip.assert_not_called()

    def test_exits_when_wifi_has_ip(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=False,
            ),
            patch(
                f"{MODULE}.enable_wifi_radio",
                return_value=True,
            ),
            patch(
                f"{MODULE}.wait_for_wifi_ip",
                return_value=True,
            ) as wait_for_ip,
            patch(f"{MODULE}.ap_connection_exists") as ap_exists,
            patch("builtins.print") as print_message,
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
                wifi_iface=" wlan9 ",
            )

        self.assertEqual(result, 0)
        wait_for_ip.assert_called_once_with(
            "wlan9",
            timeout_seconds=5,
        )
        ap_exists.assert_not_called()
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: wifi has IP, exiting"),
        )

    def test_reports_missing_ap_connection(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=False,
            ),
            patch(
                f"{MODULE}.enable_wifi_radio",
                return_value=True,
            ),
            patch(
                f"{MODULE}.wait_for_wifi_ip",
                return_value=False,
            ),
            patch(
                f"{MODULE}.ap_connection_exists",
                return_value=False,
            ) as ap_exists,
            patch(f"{MODULE}.dynamic_ssid") as dynamic_ssid,
            patch("builtins.print") as print_message,
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
                ap_name=" PiAP ",
            )

        self.assertEqual(result, 1)
        ap_exists.assert_called_once_with("PiAP")
        dynamic_ssid.assert_not_called()
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: AP connection not found: PiAP"),
        )

    def test_starts_access_point(self) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=False,
            ),
            patch(
                f"{MODULE}.enable_wifi_radio",
                return_value=True,
            ),
            patch(
                f"{MODULE}.wait_for_wifi_ip",
                return_value=False,
            ),
            patch(
                f"{MODULE}.ap_connection_exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.dynamic_ssid",
                return_value="Betabox-7eea",
            ) as dynamic_ssid,
            patch(
                f"{MODULE}.set_ap_ssid",
                return_value=True,
            ) as set_ssid,
            patch(
                f"{MODULE}.start_ap",
                return_value=True,
            ) as start_ap_call,
            patch("builtins.print") as print_message,
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
                ap_name="PiAP",
                ssid_prefix="Betabox",
                dry_run=True,
            )

        self.assertEqual(result, 0)
        dynamic_ssid.assert_called_once_with("Betabox")
        set_ssid.assert_called_once_with(
            "PiAP",
            "Betabox-7eea",
            dry_run=True,
        )
        start_ap_call.assert_called_once_with(
            "PiAP",
            dry_run=True,
        )
        self.assertEqual(
            print_message.call_args_list[-1],
            call("wifi-fallback: AP started"),
        )

    def test_stops_when_setting_ssid_fails(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=False,
            ),
            patch(
                f"{MODULE}.enable_wifi_radio",
                return_value=True,
            ),
            patch(
                f"{MODULE}.wait_for_wifi_ip",
                return_value=False,
            ),
            patch(
                f"{MODULE}.ap_connection_exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.dynamic_ssid",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.set_ap_ssid",
                return_value=False,
            ),
            patch(f"{MODULE}.start_ap") as start_ap_call,
            patch("builtins.print"),
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
            )

        self.assertEqual(result, 1)
        start_ap_call.assert_not_called()

    def test_stops_when_starting_ap_fails(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=False,
            ),
            patch(
                f"{MODULE}.enable_wifi_radio",
                return_value=True,
            ),
            patch(
                f"{MODULE}.wait_for_wifi_ip",
                return_value=False,
            ),
            patch(
                f"{MODULE}.ap_connection_exists",
                return_value=True,
            ),
            patch(
                f"{MODULE}.dynamic_ssid",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.set_ap_ssid",
                return_value=True,
            ),
            patch(
                f"{MODULE}.start_ap",
                return_value=False,
            ),
            patch("builtins.print"),
        ):
            result = run_wifi_fallback(
                delay_seconds=0,
            )

        self.assertEqual(result, 1)

    def test_uses_config_defaults(self) -> None:
        network = DEFAULT_PLATFORM_CONFIG.network

        with (
            patch(
                f"{MODULE}.nmcli_available",
                return_value=True,
            ),
            patch(f"{MODULE}.time.sleep"),
            patch(
                f"{MODULE}.ethernet_connected",
                return_value=True,
            ) as ethernet,
            patch("builtins.print"),
        ):
            result = run_wifi_fallback()

        self.assertEqual(result, 0)
        ethernet.assert_called_once_with(network.ethernet_interface)

    def test_rejects_invalid_config_before_output(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            run_wifi_fallback(
                config=object(),  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_invalid_delay_before_output(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                ValueError,
                ("delay_seconds cannot be negative"),
            ),
        ):
            run_wifi_fallback(
                delay_seconds=-1,
            )

        print_message.assert_not_called()

    def test_rejects_empty_interface_before_output(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                ValueError,
                "wifi_iface cannot be empty",
            ),
        ):
            run_wifi_fallback(
                wifi_iface=" ",
            )

        print_message.assert_not_called()


class ParseArgsTests(unittest.TestCase):
    def test_uses_config_defaults(self) -> None:
        network = DEFAULT_PLATFORM_CONFIG.network

        args = parse_args([])

        self.assertIsInstance(
            args,
            argparse.Namespace,
        )
        self.assertEqual(
            args.delay,
            network.wifi_fallback_delay_seconds,
        )
        self.assertEqual(
            args.wifi_iface,
            network.wifi_interface,
        )
        self.assertEqual(
            args.eth_iface,
            network.ethernet_interface,
        )
        self.assertEqual(
            args.ap_name,
            network.ap_connection_name,
        )
        self.assertEqual(
            args.ssid_prefix,
            network.identity_prefix,
        )
        self.assertFalse(args.dry_run)

    def test_parses_all_options(self) -> None:
        args = parse_args(
            [
                "--delay",
                "10",
                "--wifi-iface",
                "wlan9",
                "--eth-iface",
                "eth9",
                "--ap-name",
                "TestAP",
                "--ssid-prefix",
                "Robot",
                "--dry-run",
            ]
        )

        self.assertEqual(args.delay, 10)
        self.assertEqual(
            args.wifi_iface,
            "wlan9",
        )
        self.assertEqual(
            args.eth_iface,
            "eth9",
        )
        self.assertEqual(
            args.ap_name,
            "TestAP",
        )
        self.assertEqual(
            args.ssid_prefix,
            "Robot",
        )
        self.assertTrue(args.dry_run)

    def test_rejects_invalid_delay_syntax(
        self,
    ) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--delay",
                    "invalid",
                ]
            )

    def test_rejects_unknown_argument(self) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--unknown",
                ]
            )

    def test_rejects_invalid_config_before_parser(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("config must be a PlatformConfig"),
        ):
            parse_args(
                [],
                config=object(),  # type: ignore[arg-type]
            )


class MainTests(unittest.TestCase):
    def make_args(
        self,
        *,
        delay: object = 5,
        wifi_iface: str = "wlan0",
        eth_iface: str = "eth0",
        ap_name: str = "PiAP",
        ssid_prefix: str = "Betabox",
        dry_run: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            delay=delay,
            wifi_iface=wifi_iface,
            eth_iface=eth_iface,
            ap_name=ap_name,
            ssid_prefix=ssid_prefix,
            dry_run=dry_run,
        )

    def test_calls_wifi_fallback(self) -> None:
        args = self.make_args(
            delay=10,
            wifi_iface="wlan9",
            eth_iface="eth9",
            ap_name="TestAP",
            ssid_prefix="Robot",
            dry_run=True,
        )

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=args,
            ) as parse,
            patch(
                f"{MODULE}.run_wifi_fallback",
                return_value=0,
            ) as run_fallback,
        ):
            result = main(
                [
                    "--dry-run",
                ]
            )

        self.assertEqual(result, 0)
        parse.assert_called_once_with(
            [
                "--dry-run",
            ],
            config=DEFAULT_PLATFORM_CONFIG,
        )
        run_fallback.assert_called_once_with(
            delay_seconds=10,
            wifi_iface="wlan9",
            eth_iface="eth9",
            ap_name="TestAP",
            ssid_prefix="Robot",
            dry_run=True,
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_preserves_nonzero_result(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_wifi_fallback",
                return_value=1,
            ),
        ):
            result = main([])

        self.assertEqual(result, 1)

    def test_reports_value_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(delay=-1),
            ),
            patch(
                f"{MODULE}.run_wifi_fallback",
                side_effect=ValueError("delay_seconds cannot be negative"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with(
            "wifi-fallback: delay_seconds cannot be negative"
        )

    def test_reports_runtime_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_wifi_fallback",
                side_effect=RuntimeError("failed to construct fallback SSID"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with(
            "wifi-fallback: failed to construct fallback SSID"
        )

    def test_reports_os_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_wifi_fallback",
                side_effect=OSError("network unavailable"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("wifi-fallback: network unavailable")

    def test_unexpected_error_propagates(
        self,
    ) -> None:
        error = AssertionError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=self.make_args(),
            ),
            patch(
                f"{MODULE}.run_wifi_fallback",
                side_effect=error,
            ),
            self.assertRaises(AssertionError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
