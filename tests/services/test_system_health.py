from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.system_checks import (
    DiskStatus,
    MemoryStatus,
    NetworkInterfaceStatus,
    SystemHealthStatus,
    TemperatureStatus,
    ThrottlingStatus,
)
from betabox_robotics.services.system_health import (
    collect_system_health,
    main,
)

MODULE = "betabox_robotics.services.system_health"


def make_temperature_status() -> TemperatureStatus:
    return TemperatureStatus(
        celsius=42.5,
        state="normal",
    )


def make_throttling_status() -> ThrottlingStatus:
    return ThrottlingStatus(
        raw="0x0",
        undervoltage_now=False,
        undervoltage_occurred=False,
        throttled_now=False,
        throttled_occurred=False,
    )


def make_memory_status() -> MemoryStatus:
    return MemoryStatus(
        total_mb=4096,
        available_mb=2048,
        used_percent=50.0,
        state="normal",
    )


def make_disk_status() -> DiskStatus:
    return DiskStatus(
        path="/",
        total_gb=64.0,
        free_gb=32.0,
        used_percent=50.0,
        state="normal",
    )


def make_ethernet_status() -> NetworkInterfaceStatus:
    return NetworkInterfaceStatus(
        name=(DEFAULT_PLATFORM_CONFIG.health.ethernet_interface),
        available=True,
        connected=False,
        state="30 (disconnected)",
        connection=None,
    )


def make_wifi_status() -> NetworkInterfaceStatus:
    return NetworkInterfaceStatus(
        name=(DEFAULT_PLATFORM_CONFIG.health.wifi_interface),
        available=True,
        connected=True,
        state="100 (connected)",
        connection="Betabox",
    )


def make_system_health_status() -> SystemHealthStatus:
    return SystemHealthStatus(
        temperature=make_temperature_status(),
        throttling=make_throttling_status(),
        memory=make_memory_status(),
        disk=make_disk_status(),
        ethernet=make_ethernet_status(),
        wifi=make_wifi_status(),
    )


class CollectSystemHealthTests(unittest.TestCase):
    def test_collects_complete_system_health(self) -> None:
        temperature = make_temperature_status()
        throttling = make_throttling_status()
        memory = make_memory_status()
        disk = make_disk_status()
        ethernet = make_ethernet_status()
        wifi = make_wifi_status()

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=temperature,
            ) as collect_temperature,
            patch(
                f"{MODULE}.collect_throttling_status",
                return_value=throttling,
            ) as collect_throttling,
            patch(
                f"{MODULE}.collect_memory_status",
                return_value=memory,
            ) as collect_memory,
            patch(
                f"{MODULE}.collect_disk_status",
                return_value=disk,
            ) as collect_disk,
            patch(
                f"{MODULE}.collect_network_interface",
                side_effect=[
                    ethernet,
                    wifi,
                ],
            ) as collect_network,
        ):
            status = collect_system_health()

        self.assertEqual(
            status,
            SystemHealthStatus(
                temperature=temperature,
                throttling=throttling,
                memory=memory,
                disk=disk,
                ethernet=ethernet,
                wifi=wifi,
            ),
        )

        collect_temperature.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_throttling.assert_called_once_with()
        collect_memory.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_disk.assert_called_once_with(config=DEFAULT_PLATFORM_CONFIG)
        self.assertEqual(
            collect_network.call_args_list,
            [
                call(DEFAULT_PLATFORM_CONFIG.health.ethernet_interface),
                call(DEFAULT_PLATFORM_CONFIG.health.wifi_interface),
            ],
        )

    def test_preserves_component_instances(self) -> None:
        temperature = make_temperature_status()
        throttling = make_throttling_status()
        memory = make_memory_status()
        disk = make_disk_status()
        ethernet = make_ethernet_status()
        wifi = make_wifi_status()

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=temperature,
            ),
            patch(
                f"{MODULE}.collect_throttling_status",
                return_value=throttling,
            ),
            patch(
                f"{MODULE}.collect_memory_status",
                return_value=memory,
            ),
            patch(
                f"{MODULE}.collect_disk_status",
                return_value=disk,
            ),
            patch(
                f"{MODULE}.collect_network_interface",
                side_effect=[
                    ethernet,
                    wifi,
                ],
            ),
        ):
            status = collect_system_health()

        self.assertIs(
            status.temperature,
            temperature,
        )
        self.assertIs(
            status.throttling,
            throttling,
        )
        self.assertIs(
            status.memory,
            memory,
        )
        self.assertIs(
            status.disk,
            disk,
        )
        self.assertIs(
            status.ethernet,
            ethernet,
        )
        self.assertIs(
            status.wifi,
            wifi,
        )

    def test_collectors_run_in_expected_order(self) -> None:
        parent = Mock()

        temperature = make_temperature_status()
        throttling = make_throttling_status()
        memory = make_memory_status()
        disk = make_disk_status()
        ethernet = make_ethernet_status()
        wifi = make_wifi_status()

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=temperature,
            ) as collect_temperature,
            patch(
                f"{MODULE}.collect_throttling_status",
                return_value=throttling,
            ) as collect_throttling,
            patch(
                f"{MODULE}.collect_memory_status",
                return_value=memory,
            ) as collect_memory,
            patch(
                f"{MODULE}.collect_disk_status",
                return_value=disk,
            ) as collect_disk,
            patch(
                f"{MODULE}.collect_network_interface",
                side_effect=[
                    ethernet,
                    wifi,
                ],
            ) as collect_network,
        ):
            parent.attach_mock(
                collect_temperature,
                "temperature",
            )
            parent.attach_mock(
                collect_throttling,
                "throttling",
            )
            parent.attach_mock(
                collect_memory,
                "memory",
            )
            parent.attach_mock(
                collect_disk,
                "disk",
            )
            parent.attach_mock(
                collect_network,
                "network",
            )

            collect_system_health()

        self.assertEqual(
            parent.mock_calls,
            [
                call.temperature(DEFAULT_PLATFORM_CONFIG),
                call.throttling(),
                call.memory(DEFAULT_PLATFORM_CONFIG),
                call.disk(config=DEFAULT_PLATFORM_CONFIG),
                call.network(DEFAULT_PLATFORM_CONFIG.health.ethernet_interface),
                call.network(DEFAULT_PLATFORM_CONFIG.health.wifi_interface),
            ],
        )

    def test_validates_config_before_collectors(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.collect_temperature_status") as collect_temperature,
            patch(f"{MODULE}.collect_throttling_status") as collect_throttling,
            patch(f"{MODULE}.collect_memory_status") as collect_memory,
            patch(f"{MODULE}.collect_disk_status") as collect_disk,
            patch(f"{MODULE}.collect_network_interface") as collect_network,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_system_health(
                object()  # type: ignore[arg-type]
            )

        collect_temperature.assert_not_called()
        collect_throttling.assert_not_called()
        collect_memory.assert_not_called()
        collect_disk.assert_not_called()
        collect_network.assert_not_called()

    def test_temperature_error_propagates(self) -> None:
        error = RuntimeError("temperature collector failed")

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_system_health()

        self.assertIs(
            context.exception,
            error,
        )

    def test_throttling_error_propagates(self) -> None:
        error = RuntimeError("throttling collector failed")

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=make_temperature_status(),
            ),
            patch(
                f"{MODULE}.collect_throttling_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_system_health()

        self.assertIs(
            context.exception,
            error,
        )

    def test_memory_error_propagates(self) -> None:
        error = RuntimeError("memory collector failed")

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=make_temperature_status(),
            ),
            patch(
                f"{MODULE}.collect_throttling_status",
                return_value=make_throttling_status(),
            ),
            patch(
                f"{MODULE}.collect_memory_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_system_health()

        self.assertIs(
            context.exception,
            error,
        )

    def test_disk_error_propagates(self) -> None:
        error = RuntimeError("disk collector failed")

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=make_temperature_status(),
            ),
            patch(
                f"{MODULE}.collect_throttling_status",
                return_value=make_throttling_status(),
            ),
            patch(
                f"{MODULE}.collect_memory_status",
                return_value=make_memory_status(),
            ),
            patch(
                f"{MODULE}.collect_disk_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_system_health()

        self.assertIs(
            context.exception,
            error,
        )

    def test_ethernet_error_propagates(self) -> None:
        error = RuntimeError("ethernet collector failed")

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=make_temperature_status(),
            ),
            patch(
                f"{MODULE}.collect_throttling_status",
                return_value=make_throttling_status(),
            ),
            patch(
                f"{MODULE}.collect_memory_status",
                return_value=make_memory_status(),
            ),
            patch(
                f"{MODULE}.collect_disk_status",
                return_value=make_disk_status(),
            ),
            patch(
                f"{MODULE}.collect_network_interface",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_system_health()

        self.assertIs(
            context.exception,
            error,
        )

    def test_wifi_error_propagates(self) -> None:
        error = RuntimeError("wifi collector failed")

        with (
            patch(
                f"{MODULE}.collect_temperature_status",
                return_value=make_temperature_status(),
            ),
            patch(
                f"{MODULE}.collect_throttling_status",
                return_value=make_throttling_status(),
            ),
            patch(
                f"{MODULE}.collect_memory_status",
                return_value=make_memory_status(),
            ),
            patch(
                f"{MODULE}.collect_disk_status",
                return_value=make_disk_status(),
            ),
            patch(
                f"{MODULE}.collect_network_interface",
                side_effect=[
                    make_ethernet_status(),
                    error,
                ],
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_system_health()

        self.assertIs(
            context.exception,
            error,
        )


class MainTests(unittest.TestCase):
    def test_prints_json_status(self) -> None:
        status = make_system_health_status()

        with (
            patch(
                f"{MODULE}.collect_system_health",
                return_value=status,
            ) as collect,
            patch("builtins.print") as print_message,
        ):
            result = main()

        self.assertEqual(
            result,
            0,
        )
        collect.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        print_message.assert_called_once_with(
            json.dumps(
                status.to_dict(),
                indent=2,
            )
        )

    def test_printed_status_is_valid_json(self) -> None:
        status = make_system_health_status()
        printed: list[str] = []

        with (
            patch(
                f"{MODULE}.collect_system_health",
                return_value=status,
            ),
            patch(
                "builtins.print",
                side_effect=printed.append,
            ),
        ):
            result = main()

        self.assertEqual(
            result,
            0,
        )
        self.assertEqual(
            len(printed),
            1,
        )
        self.assertEqual(
            json.loads(printed[0]),
            status.to_dict(),
        )

    def test_collection_error_propagates(self) -> None:
        error = RuntimeError("system health collection failed")

        with (
            patch(
                f"{MODULE}.collect_system_health",
                side_effect=error,
            ),
            patch("builtins.print") as print_message,
            self.assertRaises(RuntimeError) as context,
        ):
            main()

        self.assertIs(
            context.exception,
            error,
        )
        print_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
