from __future__ import annotations

import subprocess
import unittest
from dataclasses import FrozenInstanceError
from types import MappingProxyType
from unittest.mock import Mock, call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnershipStatus,
)
from betabox_robotics.services.hardware_checks import (
    BatteryStatus,
    VisionStatus,
)
from betabox_robotics.services.managed import (
    ManagedService,
)
from betabox_robotics.services.platform_summary import (
    PlatformHardwareSummary,
    PlatformSummary,
    _validate_config,
    _validate_string,
    collect_platform_summary,
    hostname,
    ip_addresses,
    service_state,
)
from betabox_robotics.services.system_checks import (
    DiskStatus,
    MemoryStatus,
    NetworkInterfaceStatus,
    SystemHealthStatus,
    TemperatureStatus,
    ThrottlingStatus,
)
from betabox_robotics.version import __version__

MODULE = "betabox_robotics.services.platform_summary"


def make_battery_status() -> BatteryStatus:
    return BatteryStatus(
        available=True,
        voltage=8.2,
        state="ok",
    )


def make_vision_status() -> VisionStatus:
    return VisionStatus(
        service_available=True,
        running=True,
        camera_running=True,
        camera_has_frame=True,
        clients=1,
    )


def make_system_health() -> SystemHealthStatus:
    return SystemHealthStatus(
        temperature=TemperatureStatus(
            celsius=42.5,
            state="normal",
        ),
        throttling=ThrottlingStatus(
            raw="0x0",
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
        ),
        memory=MemoryStatus(
            total_mb=4096,
            available_mb=2048,
            used_percent=50.0,
            state="normal",
        ),
        disk=DiskStatus(
            path="/",
            total_gb=64.0,
            free_gb=32.0,
            used_percent=50.0,
            state="normal",
        ),
        ethernet=NetworkInterfaceStatus(
            name="eth0",
            available=True,
            connected=False,
            state="30 (disconnected)",
            connection=None,
        ),
        wifi=NetworkInterfaceStatus(
            name="wlan0",
            available=True,
            connected=True,
            state="100 (connected)",
            connection="Betabox",
        ),
    )


def make_control_status() -> Mock:
    control = Mock(spec=RobotOwnershipStatus)
    control.to_dict.return_value = {
        "available": True,
        "owner": None,
    }

    return control


def make_hardware_summary() -> PlatformHardwareSummary:
    return PlatformHardwareSummary(
        battery=make_battery_status(),
        vision=make_vision_status(),
    )


def make_platform_summary() -> PlatformSummary:
    return PlatformSummary(
        version=__version__,
        hostname="Betabox-7eea",
        ip_addresses=(
            "192.168.1.145",
            "10.42.0.1",
        ),
        services={
            "betabox-launchpad.service": "active",
            "jupyterhub.service": "active",
        },
        jupyterhub_proxy_available=True,
        control=make_control_status(),
        hardware=make_hardware_summary(),
        system_health=make_system_health(),
    )


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
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "config must be a PlatformConfig",
                ),
            ):
                _validate_config(value)


class ValidateStringTests(unittest.TestCase):
    def test_accepts_and_strips_string(self) -> None:
        self.assertEqual(
            _validate_string(
                " active ",
                name="state",
            ),
            "active",
        )

    def test_rejects_invalid_type(self) -> None:
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
                    "unit must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="unit",
                )

    def test_rejects_empty_string(self) -> None:
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
                    "unit cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="unit",
                )


class PlatformHardwareSummaryTests(unittest.TestCase):
    def test_accepts_valid_statuses(self) -> None:
        battery = make_battery_status()
        vision = make_vision_status()

        summary = PlatformHardwareSummary(
            battery=battery,
            vision=vision,
        )

        self.assertIs(
            summary.battery,
            battery,
        )
        self.assertIs(
            summary.vision,
            vision,
        )

    def test_rejects_invalid_battery(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "battery must be a BatteryStatus",
        ):
            PlatformHardwareSummary(
                battery=object(),  # type: ignore[arg-type]
                vision=make_vision_status(),
            )

    def test_rejects_invalid_vision(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "vision must be a VisionStatus",
        ):
            PlatformHardwareSummary(
                battery=make_battery_status(),
                vision=object(),  # type: ignore[arg-type]
            )

    def test_to_dict(self) -> None:
        summary = make_hardware_summary()

        self.assertEqual(
            summary.to_dict(),
            {
                "battery": (summary.battery.to_dict()),
                "vision": (summary.vision.to_dict()),
            },
        )

    def test_is_frozen(self) -> None:
        summary = make_hardware_summary()

        with self.assertRaises(FrozenInstanceError):
            summary.battery = (  # type: ignore[misc]
                make_battery_status()
            )

    def test_uses_slots(self) -> None:
        summary = make_hardware_summary()

        self.assertFalse(
            hasattr(
                summary,
                "__dict__",
            )
        )


class PlatformSummaryTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        summary = make_platform_summary()

        self.assertEqual(
            summary.version,
            __version__,
        )
        self.assertEqual(
            summary.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            summary.ip_addresses,
            (
                "192.168.1.145",
                "10.42.0.1",
            ),
        )

    def test_strips_version_and_hostname(self) -> None:
        control = make_control_status()

        summary = PlatformSummary(
            version=" 1.0.0 ",
            hostname=" Betabox-7eea ",
            ip_addresses=(),
            services={},
            jupyterhub_proxy_available=False,
            control=control,
            hardware=make_hardware_summary(),
            system_health=make_system_health(),
        )

        self.assertEqual(
            summary.version,
            "1.0.0",
        )
        self.assertEqual(
            summary.hostname,
            "Betabox-7eea",
        )

    def test_rejects_invalid_version(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "version must be a string",
        ):
            PlatformSummary(
                version=1,  # type: ignore[arg-type]
                hostname="Betabox",
                ip_addresses=(),
                services={},
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_empty_hostname(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "hostname cannot be empty",
        ):
            PlatformSummary(
                version="1.0.0",
                hostname=" ",
                ip_addresses=(),
                services={},
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_non_tuple_ip_addresses(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "ip_addresses must be a tuple",
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=[],  # type: ignore[arg-type]
                services={},
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_invalid_ip_address(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "IP address must be a string",
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(
                    123,  # type: ignore[arg-type]
                ),
                services={},
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_empty_ip_address(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "IP address cannot be empty",
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(" ",),
                services={},
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_non_mapping_services(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "services must be a mapping",
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                services=[],  # type: ignore[arg-type]
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_normalizes_services_to_read_only_mapping(
        self,
    ) -> None:
        services = {
            " service.service ": " active ",
        }

        summary = PlatformSummary(
            version="1.0.0",
            hostname="Betabox",
            ip_addresses=(),
            services=services,
            jupyterhub_proxy_available=False,
            control=make_control_status(),
            hardware=make_hardware_summary(),
            system_health=make_system_health(),
        )

        self.assertEqual(
            dict(summary.services),
            {
                "service.service": "active",
            },
        )
        self.assertIsInstance(
            summary.services,
            MappingProxyType,
        )

        services["another.service"] = "failed"

        self.assertNotIn(
            "another.service",
            summary.services,
        )

    def test_rejects_invalid_service_unit(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "service unit must be a string",
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                services={
                    1: "active",  # type: ignore[dict-item]
                },
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_invalid_service_state(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "service state must be a string",
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                services={
                    "service.service": 1,  # type: ignore[dict-item]
                },
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_non_boolean_proxy_state(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("jupyterhub_proxy_available must be a boolean"),
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                services={},
                jupyterhub_proxy_available=1,  # type: ignore[arg-type]
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_invalid_control(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("control must be a RobotOwnershipStatus"),
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                services={},
                jupyterhub_proxy_available=False,
                control=object(),  # type: ignore[arg-type]
                hardware=make_hardware_summary(),
                system_health=make_system_health(),
            )

    def test_rejects_invalid_hardware(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("hardware must be a PlatformHardwareSummary"),
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                services={},
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=object(),  # type: ignore[arg-type]
                system_health=make_system_health(),
            )

    def test_rejects_invalid_system_health(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("system_health must be a SystemHealthStatus"),
        ):
            PlatformSummary(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                services={},
                jupyterhub_proxy_available=False,
                control=make_control_status(),
                hardware=make_hardware_summary(),
                system_health=object(),  # type: ignore[arg-type]
            )

    def test_to_dict(self) -> None:
        summary = make_platform_summary()

        result = summary.to_dict()

        self.assertEqual(
            result,
            {
                "version": summary.version,
                "hostname": summary.hostname,
                "ip_addresses": list(summary.ip_addresses),
                "services": dict(summary.services),
                "jupyterhub_proxy_available": (summary.jupyterhub_proxy_available),
                "control": (summary.control.to_dict()),
                "hardware": (summary.hardware.to_dict()),
                "system_health": (summary.system_health.to_dict()),
            },
        )

    def test_is_frozen(self) -> None:
        summary = make_platform_summary()

        with self.assertRaises(FrozenInstanceError):
            summary.hostname = "changed"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        summary = make_platform_summary()

        self.assertFalse(
            hasattr(
                summary,
                "__dict__",
            )
        )


class HostnameTests(unittest.TestCase):
    def test_returns_socket_hostname(self) -> None:
        with patch(
            f"{MODULE}.socket.gethostname",
            return_value="Betabox-7eea",
        ) as gethostname:
            result = hostname()

        self.assertEqual(
            result,
            "Betabox-7eea",
        )
        gethostname.assert_called_once_with()

    def test_strips_hostname(self) -> None:
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

    def test_socket_error_propagates(self) -> None:
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
    def test_collects_unique_non_loopback_addresses(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("192.168.1.145 127.0.0.1 10.42.0.1 192.168.1.145\n"),
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
                "192.168.1.145",
                "10.42.0.1",
            ),
        )

    def test_preserves_ipv6_addresses(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("192.168.1.145 fd4a:38ce::1234\n"),
            ),
        ):
            result = ip_addresses()

        self.assertEqual(
            result,
            (
                "192.168.1.145",
                "fd4a:38ce::1234",
            ),
        )

    def test_returns_empty_when_command_cannot_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = ip_addresses()

        self.assertEqual(
            result,
            (),
        )

    def test_returns_empty_for_failed_command(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="failed",
            ),
        ):
            result = ip_addresses()

        self.assertEqual(
            result,
            (),
        )

    def test_returns_empty_for_empty_output(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=" \n",
            ),
        ):
            result = ip_addresses()

        self.assertEqual(
            result,
            (),
        )

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
            ip_addresses()

        self.assertIs(
            context.exception,
            error,
        )


class ServiceStateTests(unittest.TestCase):
    def test_returns_active_state(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="active\n",
            ),
        ) as run:
            result = service_state(" service.service ")

        run.assert_called_once_with(
            [
                "systemctl",
                "is-active",
                "service.service",
            ],
            timeout=3,
        )
        self.assertEqual(
            result,
            "active",
        )

    def test_returns_inactive_from_nonzero_result(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=3,
                stdout="inactive\n",
            ),
        ):
            result = service_state("service.service")

        self.assertEqual(
            result,
            "inactive",
        )

    def test_returns_failed_state(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=3,
                stdout="failed\n",
            ),
        ):
            result = service_state("service.service")

        self.assertEqual(
            result,
            "failed",
        )

    def test_uses_stderr_when_stdout_is_empty(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="systemctl failed\n",
            ),
        ):
            result = service_state("service.service")

        self.assertEqual(
            result,
            "systemctl failed",
        )

    def test_returns_unknown_for_empty_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(),
        ):
            result = service_state("service.service")

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
            result = service_state("service.service")

        self.assertEqual(
            result,
            "unknown",
        )

    def test_rejects_invalid_unit_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "unit must be a string",
            ),
        ):
            service_state(
                123  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_rejects_empty_unit_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                "unit cannot be empty",
            ),
        ):
            service_state(" ")

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
            service_state("service.service")

        self.assertIs(
            context.exception,
            error,
        )


class CollectPlatformSummaryTests(unittest.TestCase):
    def test_collects_complete_summary(self) -> None:
        managed = {
            "launchpad": ManagedService(
                name="launchpad",
                title="Launchpad",
                unit="betabox-launchpad.service",
            ),
            "jupyterhub": ManagedService(
                name="jupyterhub",
                title="JupyterHub",
                unit="jupyterhub.service",
            ),
        }
        battery = make_battery_status()
        vision = make_vision_status()
        control = make_control_status()
        system_health = make_system_health()

        with (
            patch(
                f"{MODULE}.managed_services",
                return_value=managed,
            ) as get_managed,
            patch(
                f"{MODULE}.service_state",
                side_effect=[
                    "active",
                    "failed",
                ],
            ) as get_state,
            patch(
                f"{MODULE}.hostname",
                return_value="Betabox-7eea",
            ) as get_hostname,
            patch(
                f"{MODULE}.ip_addresses",
                return_value=("192.168.1.145",),
            ) as get_addresses,
            patch(
                f"{MODULE}.shutil.which",
                return_value=("/usr/bin/configurable-http-proxy"),
            ) as which,
            patch(
                f"{MODULE}.probe_robot_ownership",
                return_value=control,
            ) as probe_control,
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ) as collect_battery,
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=vision,
            ) as collect_vision,
            patch(
                f"{MODULE}.collect_system_health",
                return_value=system_health,
            ) as collect_health,
        ):
            result = collect_platform_summary()

        self.assertEqual(
            result.version,
            __version__,
        )
        self.assertEqual(
            result.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            result.ip_addresses,
            ("192.168.1.145",),
        )
        self.assertEqual(
            dict(result.services),
            {
                "betabox-launchpad.service": ("active"),
                "jupyterhub.service": "failed",
            },
        )
        self.assertTrue(result.jupyterhub_proxy_available)
        self.assertIs(
            result.control,
            control,
        )
        self.assertIs(
            result.hardware.battery,
            battery,
        )
        self.assertIs(
            result.hardware.vision,
            vision,
        )
        self.assertIs(
            result.system_health,
            system_health,
        )

        get_managed.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        self.assertEqual(
            get_state.call_args_list,
            [
                call("betabox-launchpad.service"),
                call("jupyterhub.service"),
            ],
        )
        get_hostname.assert_called_once_with()
        get_addresses.assert_called_once_with()
        which.assert_called_once_with("configurable-http-proxy")
        probe_control.assert_called_once_with()
        collect_battery.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_vision.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_health.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)

    def test_proxy_is_unavailable_when_not_found(
        self,
    ) -> None:
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
                f"{MODULE}.shutil.which",
                return_value=None,
            ),
            patch(
                f"{MODULE}.probe_robot_ownership",
                return_value=make_control_status(),
            ),
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=make_battery_status(),
            ),
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=make_vision_status(),
            ),
            patch(
                f"{MODULE}.collect_system_health",
                return_value=make_system_health(),
            ),
        ):
            result = collect_platform_summary()

        self.assertFalse(result.jupyterhub_proxy_available)

    def test_rejects_invalid_config_before_dependencies(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.managed_services") as get_managed,
            patch(f"{MODULE}.hostname") as get_hostname,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_platform_summary(
                object()  # type: ignore[arg-type]
            )

        get_managed.assert_not_called()
        get_hostname.assert_not_called()

    def test_dependency_error_propagates(self) -> None:
        error = RuntimeError("service collection failed")

        with (
            patch(
                f"{MODULE}.managed_services",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_platform_summary()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
