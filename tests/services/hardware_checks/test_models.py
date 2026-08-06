from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.services.hardware_checks.models import (
    AudioStatus,
    BatteryStatus,
    I2CStatus,
    RobotHardwareStatus,
    SensorStatus,
    VisionStatus,
)


class I2CStatusTests(unittest.TestCase):
    def test_create(self) -> None:
        status = I2CStatus(
            available=True,
            devices=(
                "0x14",
                "0x40",
            ),
        )

        self.assertTrue(status.available)
        self.assertEqual(
            status.devices,
            (
                "0x14",
                "0x40",
            ),
        )
        self.assertIsNone(status.error)

    def test_to_dict_converts_devices_to_list(self) -> None:
        status = I2CStatus(
            available=True,
            devices=(
                "0x14",
                "0x40",
            ),
            error=None,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "available": True,
                "devices": [
                    "0x14",
                    "0x40",
                ],
                "error": None,
            },
        )

    def test_is_frozen(self) -> None:
        status = I2CStatus(
            available=False,
            devices=(),
        )

        with self.assertRaises(FrozenInstanceError):
            status.available = True  # type: ignore[misc]


class BatteryStatusTests(unittest.TestCase):
    def test_create_available_status(self) -> None:
        status = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )

        self.assertTrue(status.available)
        self.assertEqual(
            status.voltage,
            8.2,
        )
        self.assertEqual(
            status.state,
            "ok",
        )
        self.assertIsNone(status.error)

    def test_create_unavailable_status(self) -> None:
        status = BatteryStatus(
            available=False,
            voltage=None,
            state="unknown",
            error="ADC unavailable",
        )

        self.assertFalse(status.available)
        self.assertIsNone(status.voltage)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "ADC unavailable",
        )

    def test_to_dict(self) -> None:
        status = BatteryStatus(
            available=True,
            voltage=7.9,
            state="low",
        )

        self.assertEqual(
            status.to_dict(),
            {
                "available": True,
                "voltage": 7.9,
                "state": "low",
                "error": None,
            },
        )

    def test_is_frozen(self) -> None:
        status = BatteryStatus(
            available=True,
            voltage=8.0,
            state="ok",
        )

        with self.assertRaises(FrozenInstanceError):
            status.voltage = 7.0  # type: ignore[misc]


class SensorStatusTests(unittest.TestCase):
    def test_create_available_status(self) -> None:
        status = SensorStatus(
            grayscale_available=True,
            grayscale_values=(
                100,
                200,
                300,
            ),
            ultrasonic_configured=True,
        )

        self.assertTrue(status.grayscale_available)
        self.assertEqual(
            status.grayscale_values,
            (
                100,
                200,
                300,
            ),
        )
        self.assertTrue(status.ultrasonic_configured)
        self.assertIsNone(status.error)

    def test_create_unavailable_status(self) -> None:
        status = SensorStatus(
            grayscale_available=False,
            grayscale_values=None,
            ultrasonic_configured=True,
            error="grayscale read failed",
        )

        self.assertFalse(status.grayscale_available)
        self.assertIsNone(status.grayscale_values)
        self.assertEqual(
            status.error,
            "grayscale read failed",
        )

    def test_to_dict_converts_values_to_list(self) -> None:
        status = SensorStatus(
            grayscale_available=True,
            grayscale_values=(
                100,
                200,
                300,
            ),
            ultrasonic_configured=False,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "grayscale_available": True,
                "grayscale_values": [
                    100,
                    200,
                    300,
                ],
                "ultrasonic_configured": False,
                "error": None,
            },
        )

    def test_to_dict_preserves_none_values(self) -> None:
        status = SensorStatus(
            grayscale_available=False,
            grayscale_values=None,
            ultrasonic_configured=False,
            error="not available",
        )

        self.assertEqual(
            status.to_dict(),
            {
                "grayscale_available": False,
                "grayscale_values": None,
                "ultrasonic_configured": False,
                "error": "not available",
            },
        )

    def test_is_frozen(self) -> None:
        status = SensorStatus(
            grayscale_available=True,
            grayscale_values=(
                1,
                2,
                3,
            ),
            ultrasonic_configured=True,
        )

        with self.assertRaises(FrozenInstanceError):
            status.error = "changed"  # type: ignore[misc]


class AudioStatusTests(unittest.TestCase):
    def test_create_available_status(self) -> None:
        status = AudioStatus(
            available=True,
            device="HifiBerry DAC",
        )

        self.assertTrue(status.available)
        self.assertEqual(
            status.device,
            "HifiBerry DAC",
        )
        self.assertIsNone(status.error)

    def test_create_unavailable_status(self) -> None:
        status = AudioStatus(
            available=False,
            device=None,
            error="device not found",
        )

        self.assertFalse(status.available)
        self.assertIsNone(status.device)
        self.assertEqual(
            status.error,
            "device not found",
        )

    def test_to_dict(self) -> None:
        status = AudioStatus(
            available=True,
            device="HifiBerry DAC",
        )

        self.assertEqual(
            status.to_dict(),
            {
                "available": True,
                "device": "HifiBerry DAC",
                "error": None,
            },
        )

    def test_is_frozen(self) -> None:
        status = AudioStatus(
            available=True,
            device="HifiBerry DAC",
        )

        with self.assertRaises(FrozenInstanceError):
            status.device = None  # type: ignore[misc]


class VisionStatusTests(unittest.TestCase):
    def test_create_available_status(self) -> None:
        status = VisionStatus(
            service_available=True,
            running=True,
            camera_running=True,
            camera_has_frame=True,
            clients=2,
        )

        self.assertTrue(status.service_available)
        self.assertTrue(status.running)
        self.assertTrue(status.camera_running)
        self.assertTrue(status.camera_has_frame)
        self.assertEqual(
            status.clients,
            2,
        )
        self.assertIsNone(status.error)

    def test_create_unavailable_status(self) -> None:
        status = VisionStatus(
            service_available=False,
            running=False,
            camera_running=False,
            camera_has_frame=False,
            clients=0,
            error="connection failed",
        )

        self.assertFalse(status.service_available)
        self.assertEqual(
            status.error,
            "connection failed",
        )

    def test_to_dict(self) -> None:
        status = VisionStatus(
            service_available=True,
            running=True,
            camera_running=True,
            camera_has_frame=False,
            clients=1,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "service_available": True,
                "running": True,
                "camera_running": True,
                "camera_has_frame": False,
                "clients": 1,
                "error": None,
            },
        )

    def test_is_frozen(self) -> None:
        status = VisionStatus(
            service_available=True,
            running=True,
            camera_running=True,
            camera_has_frame=True,
            clients=0,
        )

        with self.assertRaises(FrozenInstanceError):
            status.clients = 3  # type: ignore[misc]


class RobotHardwareStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.i2c = I2CStatus(
            available=True,
            devices=(
                "0x14",
                "0x40",
            ),
        )
        self.battery = BatteryStatus(
            available=True,
            voltage=8.1,
            state="ok",
        )
        self.sensors = SensorStatus(
            grayscale_available=True,
            grayscale_values=(
                100,
                200,
                300,
            ),
            ultrasonic_configured=True,
        )
        self.audio = AudioStatus(
            available=True,
            device="HifiBerry DAC",
        )
        self.vision = VisionStatus(
            service_available=True,
            running=True,
            camera_running=True,
            camera_has_frame=True,
            clients=1,
        )

    def test_create(self) -> None:
        status = RobotHardwareStatus(
            i2c=self.i2c,
            passive_hardware_available=True,
            battery=self.battery,
            sensors=self.sensors,
            audio=self.audio,
            vision=self.vision,
        )

        self.assertIs(
            status.i2c,
            self.i2c,
        )
        self.assertTrue(status.passive_hardware_available)
        self.assertIs(
            status.battery,
            self.battery,
        )
        self.assertIs(
            status.sensors,
            self.sensors,
        )
        self.assertIs(
            status.audio,
            self.audio,
        )
        self.assertIs(
            status.vision,
            self.vision,
        )
        self.assertIsNone(status.passive_hardware_error)

    def test_to_dict(self) -> None:
        status = RobotHardwareStatus(
            i2c=self.i2c,
            passive_hardware_available=True,
            battery=self.battery,
            sensors=self.sensors,
            audio=self.audio,
            vision=self.vision,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "i2c": {
                    "available": True,
                    "devices": [
                        "0x14",
                        "0x40",
                    ],
                    "error": None,
                },
                "passive_hardware_available": True,
                "battery": {
                    "available": True,
                    "voltage": 8.1,
                    "state": "ok",
                    "error": None,
                },
                "sensors": {
                    "grayscale_available": True,
                    "grayscale_values": [
                        100,
                        200,
                        300,
                    ],
                    "ultrasonic_configured": True,
                    "error": None,
                },
                "audio": {
                    "available": True,
                    "device": "HifiBerry DAC",
                    "error": None,
                },
                "vision": {
                    "service_available": True,
                    "running": True,
                    "camera_running": True,
                    "camera_has_frame": True,
                    "clients": 1,
                    "error": None,
                },
                "passive_hardware_error": None,
            },
        )

    def test_to_dict_includes_passive_error(self) -> None:
        status = RobotHardwareStatus(
            i2c=self.i2c,
            passive_hardware_available=False,
            battery=BatteryStatus(
                available=False,
                voltage=None,
                state="unknown",
                error="battery failed",
            ),
            sensors=self.sensors,
            audio=self.audio,
            vision=self.vision,
            passive_hardware_error=("battery failed"),
        )

        self.assertEqual(
            status.to_dict()["passive_hardware_error"],
            "battery failed",
        )

    def test_is_frozen(self) -> None:
        status = RobotHardwareStatus(
            i2c=self.i2c,
            passive_hardware_available=True,
            battery=self.battery,
            sensors=self.sensors,
            audio=self.audio,
            vision=self.vision,
        )

        with self.assertRaises(FrozenInstanceError):
            status.passive_hardware_available = (  # type: ignore[misc]
                False
            )


if __name__ == "__main__":
    unittest.main()
