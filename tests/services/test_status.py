from __future__ import annotations

import argparse
import json
import subprocess
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnershipStatus,
)
from betabox_robotics.services.guest import (
    GuestWorkspaceStatus,
)
from betabox_robotics.services.hardware_status import (
    RobotHardwareStatus,
)
from betabox_robotics.services.status import (
    StatusReport,
    _validate_config,
    _validate_flag,
    _validate_string,
    collect_status,
    executable_available,
    format_boolean,
    hostname,
    ip_addresses,
    main,
    parse_args,
    path_available,
    print_hardware_status,
    print_human,
    print_json,
    print_system_health,
    service_status,
)
from betabox_robotics.services.system_health import (
    SystemHealthStatus,
)
from betabox_robotics.version import __version__

MODULE = "betabox_robotics.services.status"


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


def typed_mock(
    model: type,
    **attributes: object,
) -> Mock:
    value = Mock(spec=model)

    for name, attribute in attributes.items():
        setattr(
            value,
            name,
            attribute,
        )

    return value


def make_guest_status(
    *,
    account_exists: bool = True,
    home_exists: bool = True,
    curriculum_exists: bool = True,
    media_exists: bool = True,
    preferences_exist: bool = True,
) -> GuestWorkspaceStatus:
    return GuestWorkspaceStatus(
        account_exists=account_exists,
        home_exists=home_exists,
        curriculum_exists=curriculum_exists,
        media_exists=media_exists,
        preferences_exist=preferences_exist,
    )


def make_hardware_status(
    *,
    passive_hardware_available: bool = True,
    i2c_available: bool = True,
    i2c_devices: tuple[str, ...] = (
        "0x14",
        "0x40",
    ),
    battery_available: bool = True,
    battery_voltage: float | None = 8.2,
    battery_state: str = "ok",
    grayscale_available: bool = True,
    grayscale_values: list[int] | None = None,
    ultrasonic_configured: bool = True,
    audio_available: bool = True,
    audio_device: str | None = "snd_rpi_hifiberry_dac",
    vision_service_available: bool = True,
    vision_running: bool = True,
    camera_running: bool = True,
    camera_has_frame: bool = True,
    vision_clients: int = 2,
) -> RobotHardwareStatus:
    if grayscale_values is None:
        grayscale_values = [
            100,
            200,
            300,
        ]

    return typed_mock(
        RobotHardwareStatus,
        passive_hardware_available=(passive_hardware_available),
        i2c=SimpleNamespace(
            available=i2c_available,
            devices=i2c_devices,
        ),
        battery=SimpleNamespace(
            available=battery_available,
            voltage=battery_voltage,
            state=battery_state,
        ),
        sensors=SimpleNamespace(
            grayscale_available=(grayscale_available),
            grayscale_values=(grayscale_values),
            ultrasonic_configured=(ultrasonic_configured),
        ),
        audio=SimpleNamespace(
            available=audio_available,
            device=audio_device,
        ),
        vision=SimpleNamespace(
            service_available=(vision_service_available),
            running=vision_running,
            camera_running=camera_running,
            camera_has_frame=camera_has_frame,
            clients=vision_clients,
        ),
    )


def make_system_health(
    *,
    temperature: float | None = 48.5,
    temperature_state: str = "ok",
    undervoltage_now: bool = False,
    throttled_now: bool = False,
    memory_percent: float | None = 42.5,
    memory_state: str = "ok",
    disk_percent: float | None = 55.5,
    disk_state: str = "ok",
    ethernet_connected: bool = True,
    wifi_connected: bool = True,
) -> SystemHealthStatus:
    return typed_mock(
        SystemHealthStatus,
        temperature=SimpleNamespace(
            celsius=temperature,
            state=temperature_state,
        ),
        throttling=SimpleNamespace(
            undervoltage_now=(undervoltage_now),
            throttled_now=throttled_now,
        ),
        memory=SimpleNamespace(
            used_percent=memory_percent,
            state=memory_state,
        ),
        disk=SimpleNamespace(
            used_percent=disk_percent,
            state=disk_state,
        ),
        ethernet=SimpleNamespace(
            connected=ethernet_connected,
        ),
        wifi=SimpleNamespace(
            connected=wifi_connected,
        ),
    )


def make_control_status() -> RobotOwnershipStatus:
    return RobotOwnershipStatus(
        available=True,
        owner=None,
        pid=None,
        acquired_at=None,
        error=None,
    )


def make_report(
    *,
    version: str = "1.0.0",
    hostname_value: str = "Betabox-7eea",
    ip_values: tuple[str, ...] = ("192.168.1.25",),
    media_paths: dict[str, str] | None = None,
    services: dict[str, str] | None = None,
    proxy_available: bool = True,
    hardware: RobotHardwareStatus | None = None,
    system_health: SystemHealthStatus | None = None,
    guest: GuestWorkspaceStatus | None = None,
) -> StatusReport:
    if media_paths is None:
        media_paths = {
            "pictures": "/home/picar/media/pictures",
            "videos": "/home/picar/media/videos",
            "sounds": "/home/picar/media/sounds",
        }

    if services is None:
        services = {
            (DEFAULT_PLATFORM_CONFIG.services.jupyterhub.unit): "active",
            (DEFAULT_PLATFORM_CONFIG.services.launchpad.unit): "active",
        }

    return StatusReport(
        version=version,
        hostname=hostname_value,
        ip_addresses=ip_values,
        media_paths=media_paths,
        services=services,
        jupyterhub_proxy_available=(proxy_available),
        control=make_control_status(),
        hardware=(hardware if hardware is not None else make_hardware_status()),
        system_health=(
            system_health if system_health is not None else make_system_health()
        ),
        guest=(guest if guest is not None else make_guest_status()),
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
            " active ",
            name="state",
        )

        self.assertEqual(
            result,
            "active",
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
                    "state must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="state",
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
                    "state cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="state",
                )

    def test_validate_flag_accepts_boolean(
        self,
    ) -> None:
        self.assertTrue(
            _validate_flag(
                True,
                name="value",
            )
        )
        self.assertFalse(
            _validate_flag(
                False,
                name="value",
            )
        )

    def test_validate_flag_rejects_non_boolean(
        self,
    ) -> None:
        for value in (
            None,
            0,
            1,
            "yes",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "value must be a boolean",
                ),
            ):
                _validate_flag(
                    value,
                    name="value",
                )


class StatusReportTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        report = make_report()

        self.assertEqual(
            report.version,
            "1.0.0",
        )
        self.assertEqual(
            report.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            report.ip_addresses,
            ("192.168.1.25",),
        )

    def test_strips_string_values(self) -> None:
        report = make_report(
            version=" 1.0.0 ",
            hostname_value=" Betabox-7eea ",
            ip_values=(" 192.168.1.25 ",),
            media_paths={
                " pictures ": " /media/pictures ",
            },
            services={
                " launchpad.service ": " active ",
            },
        )

        self.assertEqual(
            report.version,
            "1.0.0",
        )
        self.assertEqual(
            report.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            report.ip_addresses,
            ("192.168.1.25",),
        )
        self.assertEqual(
            report.media_paths,
            {
                "pictures": "/media/pictures",
            },
        )
        self.assertEqual(
            report.services,
            {
                "launchpad.service": "active",
            },
        )

    def test_rejects_non_tuple_addresses(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("ip_addresses must be a tuple"),
        ):
            make_report(
                ip_values=[  # type: ignore[arg-type]
                    "192.168.1.25"
                ]
            )

    def test_rejects_invalid_media_paths(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("media_paths must be a dictionary"),
        ):
            make_report(
                media_paths=[]  # type: ignore[arg-type]
            )

    def test_rejects_invalid_services(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("services must be a dictionary"),
        ):
            make_report(
                services=[]  # type: ignore[arg-type]
            )

    def test_rejects_invalid_proxy_flag(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("jupyterhub_proxy_available must be a boolean"),
        ):
            make_report(
                proxy_available=1,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_control(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("control must be a RobotOwnershipStatus"),
        ):
            StatusReport(
                version="1.0",
                hostname="Betabox",
                ip_addresses=(),
                media_paths={},
                services={},
                jupyterhub_proxy_available=True,
                control=object(),  # type: ignore[arg-type]
                hardware=make_hardware_status(),
                system_health=make_system_health(),
                guest=make_guest_status(),
            )

    def test_to_dict_returns_nested_dictionary(
        self,
    ) -> None:
        report = make_report()

        result = report.to_dict()

        self.assertEqual(
            result["version"],
            "1.0.0",
        )
        self.assertEqual(
            result["hostname"],
            "Betabox-7eea",
        )
        self.assertEqual(
            result["guest"]["account_exists"],
            True,
        )

    def test_is_frozen_and_slotted(
        self,
    ) -> None:
        report = make_report()

        self.assertFalse(
            hasattr(
                report,
                "__dict__",
            )
        )

        with self.assertRaises(FrozenInstanceError):
            report.hostname = "changed"  # type: ignore[misc]


class HostnameTests(unittest.TestCase):
    def test_returns_hostname(self) -> None:
        with patch(
            f"{MODULE}.socket.gethostname",
            return_value=" Betabox-7eea ",
        ):
            result = hostname()

        self.assertEqual(
            result,
            "Betabox-7eea",
        )

    def test_rejects_empty_hostname(self) -> None:
        with (
            patch(
                f"{MODULE}.socket.gethostname",
                return_value=" ",
            ),
            self.assertRaisesRegex(
                ValueError,
                "hostname cannot be empty",
            ),
        ):
            hostname()

    def test_unexpected_socket_error_propagates(
        self,
    ) -> None:
        error = OSError("hostname unavailable")

        with (
            patch(
                f"{MODULE}.socket.gethostname",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            hostname()

        self.assertIs(
            context.exception,
            error,
        )


class IpAddressesTests(unittest.TestCase):
    def test_returns_filtered_unique_addresses(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("192.168.1.25 127.0.0.1 0.0.0.0 :: ::1 fe80::1 192.168.1.25\n"),
            ),
        ) as run:
            result = ip_addresses()

        run.assert_called_once_with(
            [
                "hostname",
                "-I",
            ],
            timeout=3,
        )
        self.assertEqual(
            result,
            (
                "192.168.1.25",
                "fe80::1",
            ),
        )

    def test_returns_empty_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            self.assertEqual(
                ip_addresses(),
                (),
            )

    def test_returns_empty_for_failed_command(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="192.168.1.25\n",
            ),
        ):
            self.assertEqual(
                ip_addresses(),
                (),
            )

    def test_unexpected_runner_error_propagates(
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
            ip_addresses()

        self.assertIs(
            context.exception,
            error,
        )


class ServiceStatusTests(unittest.TestCase):
    def test_returns_stdout_state(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=3,
                stdout="inactive\n",
            ),
        ) as run:
            result = service_status(" launchpad.service ")

        run.assert_called_once_with(
            [
                "systemctl",
                "is-active",
                "launchpad.service",
            ],
            timeout=3,
        )
        self.assertEqual(
            result,
            "inactive",
        )

    def test_uses_stderr_fallback(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="failed\n",
            ),
        ):
            result = service_status("launchpad.service")

        self.assertEqual(
            result,
            "failed",
        )

    def test_returns_unknown_without_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(returncode=1),
        ):
            result = service_status("launchpad.service")

        self.assertEqual(
            result,
            "unknown",
        )

    def test_returns_unknown_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = service_status("launchpad.service")

        self.assertEqual(
            result,
            "unknown",
        )

    def test_rejects_empty_service_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                "service cannot be empty",
            ),
        ):
            service_status(" ")

        run.assert_not_called()


class ExecutableAvailableTests(unittest.TestCase):
    def test_returns_true_when_found(self) -> None:
        with patch(
            f"{MODULE}.shutil.which",
            return_value=("/usr/bin/configurable-http-proxy"),
        ) as which:
            result = executable_available(" configurable-http-proxy ")

        which.assert_called_once_with("configurable-http-proxy")
        self.assertTrue(result)

    def test_returns_false_when_missing(self) -> None:
        with patch(
            f"{MODULE}.shutil.which",
            return_value=None,
        ):
            self.assertFalse(executable_available("configurable-http-proxy"))

    def test_rejects_empty_command_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.shutil.which") as which,
            self.assertRaisesRegex(
                ValueError,
                "command cannot be empty",
            ),
        ):
            executable_available(" ")

        which.assert_not_called()


class CollectStatusTests(unittest.TestCase):
    def test_collects_complete_status(
        self,
    ) -> None:
        service_one = SimpleNamespace(
            unit="launchpad.service",
        )
        service_two = SimpleNamespace(
            unit="jupyterhub.service",
        )
        managed = {
            "launchpad": service_one,
            "jupyterhub": service_two,
        }
        hardware = make_hardware_status()
        health = make_system_health()
        control = make_control_status()
        guest = make_guest_status()

        with (
            patch(
                f"{MODULE}.managed_services",
                return_value=managed,
            ) as managed_services,
            patch(
                f"{MODULE}.service_status",
                side_effect=(
                    "active",
                    "inactive",
                ),
            ) as get_service_status,
            patch(
                f"{MODULE}.hostname",
                return_value="Betabox-7eea",
            ),
            patch(
                f"{MODULE}.ip_addresses",
                return_value=("192.168.1.25",),
            ),
            patch(
                f"{MODULE}.executable_available",
                return_value=True,
            ) as executable,
            patch(
                f"{MODULE}.probe_robot_ownership",
                return_value=control,
            ),
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=hardware,
            ) as collect_hardware,
            patch(
                f"{MODULE}.collect_system_health",
                return_value=health,
            ) as collect_health,
            patch(
                f"{MODULE}.guest_status",
                return_value=guest,
            ) as collect_guest,
        ):
            result = collect_status()

        managed_services.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        self.assertEqual(
            get_service_status.call_args_list,
            [
                call("launchpad.service"),
                call("jupyterhub.service"),
            ],
        )
        executable.assert_called_once_with("configurable-http-proxy")
        collect_hardware.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_health.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_guest.assert_called_once_with()

        self.assertEqual(
            result.version,
            __version__,
        )
        self.assertEqual(
            result.services,
            {
                "launchpad.service": "active",
                "jupyterhub.service": "inactive",
            },
        )
        self.assertIs(
            result.hardware,
            hardware,
        )
        self.assertIs(
            result.system_health,
            health,
        )
        self.assertIs(
            result.guest,
            guest,
        )

    def test_rejects_invalid_config_before_collection(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.managed_services") as managed,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            collect_status(
                object()  # type: ignore[arg-type]
            )

        managed.assert_not_called()

    def test_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("hardware failed")

        with (
            patch(
                f"{MODULE}.managed_services",
                return_value={},
            ),
            patch(
                f"{MODULE}.hostname",
                return_value="Betabox",
            ),
            patch(
                f"{MODULE}.ip_addresses",
                return_value=(),
            ),
            patch(
                f"{MODULE}.executable_available",
                return_value=True,
            ),
            patch(
                f"{MODULE}.probe_robot_ownership",
                return_value=make_control_status(),
            ),
            patch(
                f"{MODULE}.collect_hardware_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_status()

        self.assertIs(
            context.exception,
            error,
        )


class FormatBooleanTests(unittest.TestCase):
    def test_formats_true(self) -> None:
        self.assertEqual(
            format_boolean(True),
            "available",
        )

    def test_formats_false(self) -> None:
        self.assertEqual(
            format_boolean(False),
            "missing",
        )

    def test_rejects_non_boolean(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be a boolean",
        ):
            format_boolean(
                1  # type: ignore[arg-type]
            )


class PathAvailableTests(unittest.TestCase):
    def test_returns_true_when_path_exists(
        self,
    ) -> None:
        with patch.object(
            Path,
            "exists",
            return_value=True,
        ):
            result = path_available(" /home/picar/media ")

        self.assertTrue(result)

    def test_returns_false_when_missing(
        self,
    ) -> None:
        with patch.object(
            Path,
            "exists",
            return_value=False,
        ):
            self.assertFalse(path_available("/missing"))

    def test_returns_false_for_os_error(
        self,
    ) -> None:
        with patch.object(
            Path,
            "exists",
            side_effect=OSError("permission denied"),
        ):
            self.assertFalse(path_available("/restricted"))

    def test_rejects_boolean_path(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("path must be a string or Path"),
            ),
        ):
            path_available(
                True  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_rejects_empty_path(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path cannot be empty",
        ):
            path_available(" ")


class PrintSystemHealthTests(unittest.TestCase):
    def test_prints_available_values(
        self,
    ) -> None:
        health = make_system_health(
            undervoltage_now=True,
            throttled_now=True,
            ethernet_connected=False,
            wifi_connected=True,
        )

        with patch("builtins.print") as print_message:
            print_system_health(health)

        self.assertIn(
            call("CPU Temp:     48.5 °C — ok"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Undervoltage: detected"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Throttling:   active"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Memory:       42.5% — ok"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Disk:         55.5% — ok"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Ethernet:     disconnected"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Wi-Fi:        connected"),
            print_message.call_args_list,
        )

    def test_prints_unavailable_values(
        self,
    ) -> None:
        health = make_system_health(
            temperature=None,
            memory_percent=None,
            disk_percent=None,
        )

        with patch("builtins.print") as print_message:
            print_system_health(health)

        self.assertIn(
            call("CPU Temp:     unavailable"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Memory:       unavailable"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Disk:         unavailable"),
            print_message.call_args_list,
        )

    def test_rejects_invalid_status_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("system_health must be a SystemHealthStatus"),
            ),
        ):
            print_system_health(
                object()  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class PrintHardwareStatusTests(unittest.TestCase):
    def test_prints_healthy_hardware(
        self,
    ) -> None:
        hardware = make_hardware_status()

        with patch("builtins.print") as print_message:
            print_hardware_status(hardware)

        self.assertIn(
            call("Passive Hardware:       available"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("I²C bus:     available"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("I²C devices: 0x14, 0x40"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Battery:     8.20 V — ok"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Vision:      healthy"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Clients:     2"),
            print_message.call_args_list,
        )

    def test_prints_unavailable_hardware(
        self,
    ) -> None:
        hardware = make_hardware_status(
            passive_hardware_available=False,
            i2c_available=False,
            i2c_devices=(),
            battery_available=False,
            battery_voltage=None,
            grayscale_available=False,
            ultrasonic_configured=False,
            audio_available=False,
            vision_service_available=False,
        )

        with patch("builtins.print") as print_message:
            print_hardware_status(hardware)

        self.assertIn(
            call("I²C devices: none detected"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Battery:     unavailable"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Grayscale:   unavailable"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Ultrasonic:  not configured"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Audio:       unavailable"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Vision:      unavailable"),
            print_message.call_args_list,
        )

    def test_prints_degraded_vision(
        self,
    ) -> None:
        hardware = make_hardware_status(
            camera_running=False,
            camera_has_frame=False,
            vision_running=True,
        )

        with patch("builtins.print") as print_message:
            print_hardware_status(hardware)

        self.assertIn(
            call("Vision:      degraded"),
            print_message.call_args_list,
        )

    def test_prints_stopped_vision(
        self,
    ) -> None:
        hardware = make_hardware_status(
            camera_running=False,
            camera_has_frame=False,
            vision_running=False,
        )

        with patch("builtins.print") as print_message:
            print_hardware_status(hardware)

        self.assertIn(
            call("Vision:      stopped"),
            print_message.call_args_list,
        )

    def test_rejects_invalid_status_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("hardware must be a RobotHardwareStatus"),
            ),
        ):
            print_hardware_status(
                object()  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class PrintJsonTests(unittest.TestCase):
    def test_prints_indented_json(self) -> None:
        report = make_report()
        payload = {
            "version": "1.0.0",
            "hostname": "Betabox-7eea",
            "ip_addresses": [
                "192.168.1.25",
            ],
        }

        with (
            patch.object(
                StatusReport,
                "to_dict",
                return_value=payload,
            ) as to_dict,
            patch("builtins.print") as print_message,
        ):
            print_json(report)

        to_dict.assert_called_once_with()
        print_message.assert_called_once_with(
            json.dumps(
                payload,
                indent=2,
            )
        )

    def test_rejects_invalid_report_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("report must be a StatusReport"),
            ),
        ):
            print_json(
                object()  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class PrintHumanTests(unittest.TestCase):
    def test_prints_report_sections(
        self,
    ) -> None:
        report = make_report()

        managed = {
            "launchpad": SimpleNamespace(
                title="Launchpad",
                unit=(DEFAULT_PLATFORM_CONFIG.services.launchpad.unit),
            ),
        }

        with (
            patch(f"{MODULE}.print_hardware_status") as print_hardware,
            patch(f"{MODULE}.print_system_health") as print_health,
            patch(
                f"{MODULE}.path_available",
                return_value=True,
            ) as path_exists,
            patch(f"{MODULE}.print_guest_status") as print_guest,
            patch(
                f"{MODULE}.managed_services",
                return_value=managed,
            ),
            patch("builtins.print") as print_message,
        ):
            print_human(report)

        print_hardware.assert_called_once_with(report.hardware)
        print_health.assert_called_once_with(report.system_health)
        print_guest.assert_called_once_with(report.guest)
        self.assertEqual(
            path_exists.call_args_list,
            [call(path) for path in (report.media_paths.values())],
        )
        self.assertIn(
            call("Betabox Status"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("Hostname: Betabox-7eea"),
            print_message.call_args_list,
        )

    def test_prints_no_ip_message(
        self,
    ) -> None:
        report = make_report(ip_values=())

        with (
            patch(f"{MODULE}.print_hardware_status"),
            patch(f"{MODULE}.print_system_health"),
            patch(
                f"{MODULE}.path_available",
                return_value=False,
            ),
            patch(f"{MODULE}.print_guest_status"),
            patch(
                f"{MODULE}.managed_services",
                return_value={},
            ),
            patch("builtins.print") as print_message,
        ):
            print_human(report)

        self.assertIn(
            call("IP:       none found"),
            print_message.call_args_list,
        )

    def test_rejects_invalid_report_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("report must be a StatusReport"),
            ),
        ):
            print_human(
                object()  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_invalid_config_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            print_human(
                make_report(),
                object(),  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class ParseArgsTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = parse_args([])

        self.assertIsInstance(
            args,
            argparse.Namespace,
        )
        self.assertFalse(args.json)

    def test_parses_json(self) -> None:
        args = parse_args(
            [
                "--json",
            ]
        )

        self.assertTrue(args.json)

    def test_rejects_unknown_argument(
        self,
    ) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--unknown",
                ]
            )


class MainTests(unittest.TestCase):
    def test_prints_human_status(self) -> None:
        report = make_report()
        args = argparse.Namespace(json=False)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=args,
            ) as parse,
            patch(
                f"{MODULE}.collect_status",
                return_value=report,
            ) as collect,
            patch(f"{MODULE}.print_human") as print_human_call,
            patch(f"{MODULE}.print_json") as print_json_call,
        ):
            result = main([])

        self.assertEqual(result, 0)
        parse.assert_called_once_with([])
        collect.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        print_human_call.assert_called_once_with(
            report,
            DEFAULT_PLATFORM_CONFIG,
        )
        print_json_call.assert_not_called()

    def test_prints_json_status(self) -> None:
        report = make_report()

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=True),
            ),
            patch(
                f"{MODULE}.collect_status",
                return_value=report,
            ),
            patch(f"{MODULE}.print_json") as print_json_call,
            patch(f"{MODULE}.print_human") as print_human_call,
        ):
            result = main(
                [
                    "--json",
                ]
            )

        self.assertEqual(result, 0)
        print_json_call.assert_called_once_with(report)
        print_human_call.assert_not_called()

    def test_reports_type_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_status",
                side_effect=TypeError("invalid status"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("status failed: invalid status")

    def test_reports_value_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_status",
                side_effect=ValueError("hostname cannot be empty"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("status failed: hostname cannot be empty")

    def test_reports_os_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_status",
                side_effect=OSError("system unavailable"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("status failed: system unavailable")

    def test_unexpected_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
