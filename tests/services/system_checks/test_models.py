from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.services.system_checks.models import (
    DiskStatus,
    MemoryStatus,
    NetworkInterfaceStatus,
    SystemHealthStatus,
    TemperatureStatus,
    ThrottlingStatus,
)


class TemperatureStatusTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        status = TemperatureStatus(
            celsius=42.5,
            state="normal",
        )

        self.assertEqual(
            status.to_dict(),
            {
                "celsius": 42.5,
                "state": "normal",
                "error": None,
            },
        )

    def test_supports_unknown_status(self) -> None:
        status = TemperatureStatus(
            celsius=None,
            state="unknown",
            error="temperature unavailable",
        )

        self.assertIsNone(status.celsius)
        self.assertEqual(
            status.error,
            "temperature unavailable",
        )

    def test_is_frozen(self) -> None:
        status = TemperatureStatus(
            celsius=42.5,
            state="normal",
        )

        with self.assertRaises(FrozenInstanceError):
            status.state = "high"  # type: ignore[misc]


class ThrottlingStatusTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        status = ThrottlingStatus(
            raw="0x50005",
            undervoltage_now=True,
            undervoltage_occurred=True,
            throttled_now=True,
            throttled_occurred=True,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "raw": "0x50005",
                "undervoltage_now": True,
                "undervoltage_occurred": True,
                "throttled_now": True,
                "throttled_occurred": True,
                "error": None,
            },
        )

    def test_supports_error_status(self) -> None:
        status = ThrottlingStatus(
            raw=None,
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
            error="vcgencmd failed",
        )

        self.assertEqual(
            status.error,
            "vcgencmd failed",
        )

    def test_is_frozen(self) -> None:
        status = ThrottlingStatus(
            raw="0x0",
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
        )

        with self.assertRaises(FrozenInstanceError):
            status.raw = "0x1"  # type: ignore[misc]


class MemoryStatusTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        status = MemoryStatus(
            total_mb=4096,
            available_mb=2048,
            used_percent=50.0,
            state="normal",
        )

        self.assertEqual(
            status.to_dict(),
            {
                "total_mb": 4096,
                "available_mb": 2048,
                "used_percent": 50.0,
                "state": "normal",
                "error": None,
            },
        )

    def test_supports_unknown_status(self) -> None:
        status = MemoryStatus(
            total_mb=None,
            available_mb=None,
            used_percent=None,
            state="unknown",
            error="meminfo unavailable",
        )

        self.assertIsNone(status.total_mb)
        self.assertIsNone(status.available_mb)
        self.assertIsNone(status.used_percent)
        self.assertEqual(
            status.error,
            "meminfo unavailable",
        )

    def test_is_frozen(self) -> None:
        status = MemoryStatus(
            total_mb=4096,
            available_mb=2048,
            used_percent=50.0,
            state="normal",
        )

        with self.assertRaises(FrozenInstanceError):
            status.used_percent = 75.0  # type: ignore[misc]


class DiskStatusTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        status = DiskStatus(
            path="/",
            total_gb=64.0,
            free_gb=32.0,
            used_percent=50.0,
            state="normal",
        )

        self.assertEqual(
            status.to_dict(),
            {
                "path": "/",
                "total_gb": 64.0,
                "free_gb": 32.0,
                "used_percent": 50.0,
                "state": "normal",
                "error": None,
            },
        )

    def test_supports_unknown_status(self) -> None:
        status = DiskStatus(
            path="/missing",
            total_gb=None,
            free_gb=None,
            used_percent=None,
            state="unknown",
            error="disk unavailable",
        )

        self.assertEqual(
            status.path,
            "/missing",
        )
        self.assertEqual(
            status.error,
            "disk unavailable",
        )

    def test_is_frozen(self) -> None:
        status = DiskStatus(
            path="/",
            total_gb=64.0,
            free_gb=32.0,
            used_percent=50.0,
            state="normal",
        )

        with self.assertRaises(FrozenInstanceError):
            status.path = "/home"  # type: ignore[misc]


class NetworkInterfaceStatusTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        status = NetworkInterfaceStatus(
            name="wlan0",
            available=True,
            connected=True,
            state="100 (connected)",
            connection="Betabox",
        )

        self.assertEqual(
            status.to_dict(),
            {
                "name": "wlan0",
                "available": True,
                "connected": True,
                "state": "100 (connected)",
                "connection": "Betabox",
                "error": None,
            },
        )

    def test_supports_unavailable_status(self) -> None:
        status = NetworkInterfaceStatus(
            name="eth0",
            available=False,
            connected=False,
            state="unknown",
            connection=None,
            error="nmcli failed",
        )

        self.assertFalse(status.available)
        self.assertFalse(status.connected)
        self.assertIsNone(status.connection)
        self.assertEqual(
            status.error,
            "nmcli failed",
        )

    def test_is_frozen(self) -> None:
        status = NetworkInterfaceStatus(
            name="wlan0",
            available=True,
            connected=True,
            state="100 (connected)",
            connection="Betabox",
        )

        with self.assertRaises(FrozenInstanceError):
            status.connected = False  # type: ignore[misc]


class SystemHealthStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temperature = TemperatureStatus(
            celsius=42.5,
            state="normal",
        )
        self.throttling = ThrottlingStatus(
            raw="0x0",
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
        )
        self.memory = MemoryStatus(
            total_mb=4096,
            available_mb=2048,
            used_percent=50.0,
            state="normal",
        )
        self.disk = DiskStatus(
            path="/",
            total_gb=64.0,
            free_gb=32.0,
            used_percent=50.0,
            state="normal",
        )
        self.ethernet = NetworkInterfaceStatus(
            name="eth0",
            available=True,
            connected=False,
            state="30 (disconnected)",
            connection=None,
        )
        self.wifi = NetworkInterfaceStatus(
            name="wlan0",
            available=True,
            connected=True,
            state="100 (connected)",
            connection="Betabox",
        )

    def test_to_dict(self) -> None:
        status = SystemHealthStatus(
            temperature=self.temperature,
            throttling=self.throttling,
            memory=self.memory,
            disk=self.disk,
            ethernet=self.ethernet,
            wifi=self.wifi,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "temperature": self.temperature.to_dict(),
                "throttling": self.throttling.to_dict(),
                "memory": self.memory.to_dict(),
                "disk": self.disk.to_dict(),
                "ethernet": self.ethernet.to_dict(),
                "wifi": self.wifi.to_dict(),
            },
        )

    def test_preserves_component_instances(self) -> None:
        status = SystemHealthStatus(
            temperature=self.temperature,
            throttling=self.throttling,
            memory=self.memory,
            disk=self.disk,
            ethernet=self.ethernet,
            wifi=self.wifi,
        )

        self.assertIs(
            status.temperature,
            self.temperature,
        )
        self.assertIs(
            status.throttling,
            self.throttling,
        )
        self.assertIs(
            status.memory,
            self.memory,
        )
        self.assertIs(
            status.disk,
            self.disk,
        )
        self.assertIs(
            status.ethernet,
            self.ethernet,
        )
        self.assertIs(
            status.wifi,
            self.wifi,
        )

    def test_is_frozen(self) -> None:
        status = SystemHealthStatus(
            temperature=self.temperature,
            throttling=self.throttling,
            memory=self.memory,
            disk=self.disk,
            ethernet=self.ethernet,
            wifi=self.wifi,
        )

        with self.assertRaises(FrozenInstanceError):
            status.temperature = self.temperature  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
