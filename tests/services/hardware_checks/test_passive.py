from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from betabox_robotics.hardware import HardwareError
from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
)
from betabox_robotics.services.hardware_checks.models import (
    BatteryStatus,
)
from betabox_robotics.services.hardware_checks.passive import (
    _validate_sensors_config,
    collect_battery_status,
    collect_robot_status,
)

MODULE = "betabox_robotics.services.hardware_checks.passive"

SENSORS_CONFIG = BETABOX_CAR.sensors


class ValidateSensorsConfigTests(unittest.TestCase):
    def test_accepts_sensors_config(self) -> None:
        result = _validate_sensors_config(SENSORS_CONFIG)

        self.assertIs(
            result,
            SENSORS_CONFIG,
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
                    ("sensors_config must be a SensorsConfig"),
                ),
            ):
                _validate_sensors_config(value)


class CollectBatteryStatusTests(unittest.TestCase):
    def test_collects_battery_status(self) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.return_value = 8.25
        battery_sensor.status.return_value = SimpleNamespace(value="ok")

        with patch(
            f"{MODULE}.Battery.default",
            return_value=battery_sensor,
        ) as default:
            status = collect_battery_status(SENSORS_CONFIG)

        default.assert_called_once_with(SENSORS_CONFIG.battery)
        battery_sensor.voltage.assert_called_once_with()
        battery_sensor.status.assert_called_once_with()
        battery_sensor.close.assert_called_once_with()

        self.assertEqual(
            status,
            BatteryStatus(
                available=True,
                voltage=8.25,
                state="ok",
            ),
        )

    def test_converts_voltage_to_float(self) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.return_value = 8
        battery_sensor.status.return_value = SimpleNamespace(value="ok")

        with patch(
            f"{MODULE}.Battery.default",
            return_value=battery_sensor,
        ):
            status = collect_battery_status(SENSORS_CONFIG)

        self.assertEqual(
            status.voltage,
            8.0,
        )
        self.assertIsInstance(
            status.voltage,
            float,
        )

    def test_returns_unavailable_when_construction_fails(
        self,
    ) -> None:
        error = HardwareError("ADC unavailable")

        with patch(
            f"{MODULE}.Battery.default",
            side_effect=error,
        ):
            status = collect_battery_status(SENSORS_CONFIG)

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

    def test_returns_unavailable_when_voltage_read_fails(
        self,
    ) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.side_effect = HardwareError("voltage read failed")

        with patch(
            f"{MODULE}.Battery.default",
            return_value=battery_sensor,
        ):
            status = collect_battery_status(SENSORS_CONFIG)

        self.assertFalse(status.available)
        self.assertIsNone(status.voltage)
        self.assertEqual(
            status.state,
            "unknown",
        )
        self.assertEqual(
            status.error,
            "voltage read failed",
        )
        battery_sensor.close.assert_called_once_with()

    def test_returns_unavailable_when_status_read_fails(
        self,
    ) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.return_value = 8.1
        battery_sensor.status.side_effect = RuntimeError("status failed")

        with patch(
            f"{MODULE}.Battery.default",
            return_value=battery_sensor,
        ):
            status = collect_battery_status(SENSORS_CONFIG)

        self.assertFalse(status.available)
        self.assertEqual(
            status.error,
            "status failed",
        )
        battery_sensor.close.assert_called_once_with()

    def test_handles_invalid_voltage_value(self) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.return_value = "not-a-voltage"

        with patch(
            f"{MODULE}.Battery.default",
            return_value=battery_sensor,
        ):
            status = collect_battery_status(SENSORS_CONFIG)

        self.assertFalse(status.available)
        self.assertIsNotNone(status.error)
        battery_sensor.close.assert_called_once_with()

    def test_suppresses_expected_close_error(self) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.return_value = 8.2
        battery_sensor.status.return_value = SimpleNamespace(value="ok")
        battery_sensor.close.side_effect = HardwareError("close failed")

        with patch(
            f"{MODULE}.Battery.default",
            return_value=battery_sensor,
        ):
            status = collect_battery_status(SENSORS_CONFIG)

        self.assertTrue(status.available)
        battery_sensor.close.assert_called_once_with()

    def test_unexpected_close_error_propagates(self) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.return_value = 8.2
        battery_sensor.status.return_value = SimpleNamespace(value="ok")
        battery_sensor.close.side_effect = LookupError("unexpected close failure")

        with (
            patch(
                f"{MODULE}.Battery.default",
                return_value=battery_sensor,
            ),
            self.assertRaises(LookupError) as context,
        ):
            collect_battery_status(SENSORS_CONFIG)

        self.assertEqual(
            str(context.exception),
            "unexpected close failure",
        )

    def test_does_not_close_when_construction_fails(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.Battery.default",
                side_effect=HardwareError("construction failed"),
            ),
            patch(f"{MODULE}.getattr") as get_attribute,
        ):
            collect_battery_status(SENSORS_CONFIG)

        get_attribute.assert_not_called()

    def test_unexpected_operational_error_propagates(
        self,
    ) -> None:
        battery_sensor = MagicMock()
        battery_sensor.voltage.side_effect = LookupError("unexpected failure")

        with (
            patch(
                f"{MODULE}.Battery.default",
                return_value=battery_sensor,
            ),
            self.assertRaises(LookupError) as context,
        ):
            collect_battery_status(SENSORS_CONFIG)

        self.assertEqual(
            str(context.exception),
            "unexpected failure",
        )
        battery_sensor.close.assert_called_once_with()

    def test_rejects_invalid_config_before_construction(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.Battery.default") as default,
            self.assertRaisesRegex(
                TypeError,
                ("sensors_config must be a SensorsConfig"),
            ),
        ):
            collect_battery_status(
                object()  # type: ignore[arg-type]
            )

        default.assert_not_called()


class CollectRobotStatusTests(unittest.TestCase):
    def test_collects_available_passive_hardware(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.return_value = [
            100,
            200,
            300,
        ]

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ) as collect_battery,
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ) as default,
        ):
            (
                available,
                result_battery,
                sensors,
                error,
            ) = collect_robot_status(SENSORS_CONFIG)

        collect_battery.assert_called_once_with(SENSORS_CONFIG)
        default.assert_called_once_with(SENSORS_CONFIG.grayscale)
        grayscale_sensor.read.assert_called_once_with()
        grayscale_sensor.close.assert_called_once_with()

        self.assertTrue(available)
        self.assertIs(
            result_battery,
            battery,
        )
        self.assertTrue(sensors.grayscale_available)
        self.assertEqual(
            sensors.grayscale_values,
            (
                100,
                200,
                300,
            ),
        )
        self.assertEqual(
            sensors.ultrasonic_configured,
            SENSORS_CONFIG.ultrasonic is not None,
        )
        self.assertIsNone(sensors.error)
        self.assertIsNone(error)

    def test_converts_grayscale_values_to_integers(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.return_value = [
            100.9,
            200.1,
            300,
        ]

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
        ):
            _, _, sensors, _ = collect_robot_status(SENSORS_CONFIG)

        self.assertEqual(
            sensors.grayscale_values,
            (
                100,
                200,
                300,
            ),
        )

    def test_reports_grayscale_construction_failure(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                side_effect=HardwareError("ADC unavailable"),
            ),
        ):
            (
                available,
                result_battery,
                sensors,
                error,
            ) = collect_robot_status(SENSORS_CONFIG)

        self.assertFalse(available)
        self.assertIs(
            result_battery,
            battery,
        )
        self.assertFalse(sensors.grayscale_available)
        self.assertIsNone(sensors.grayscale_values)
        self.assertEqual(
            sensors.error,
            ("passive sensors could not be constructed"),
        )
        self.assertEqual(
            error,
            "ADC unavailable",
        )

    def test_reports_grayscale_read_failure(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.side_effect = HardwareError("read failed")

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
        ):
            (
                available,
                _,
                sensors,
                error,
            ) = collect_robot_status(SENSORS_CONFIG)

        self.assertFalse(available)
        self.assertFalse(sensors.grayscale_available)
        self.assertIsNone(sensors.grayscale_values)
        self.assertEqual(
            sensors.error,
            "read failed",
        )
        self.assertEqual(
            error,
            "read failed",
        )
        grayscale_sensor.close.assert_called_once_with()

    def test_battery_failure_makes_hardware_unavailable(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=False,
            voltage=None,
            state="unknown",
            error="battery failed",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.return_value = [
            1,
            2,
            3,
        ]

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
        ):
            (
                available,
                _,
                sensors,
                error,
            ) = collect_robot_status(SENSORS_CONFIG)

        self.assertFalse(available)
        self.assertTrue(sensors.grayscale_available)
        self.assertEqual(
            error,
            "battery failed",
        )

    def test_battery_error_takes_precedence_over_sensor_error(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=False,
            voltage=None,
            state="unknown",
            error="battery failed",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.side_effect = HardwareError("sensor failed")

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
        ):
            (
                available,
                _,
                sensors,
                error,
            ) = collect_robot_status(SENSORS_CONFIG)

        self.assertFalse(available)
        self.assertEqual(
            sensors.error,
            "sensor failed",
        )
        self.assertEqual(
            error,
            "battery failed",
        )

    def test_error_is_none_when_unavailable_without_messages(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=False,
            voltage=None,
            state="unknown",
            error=None,
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.side_effect = ValueError("")

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
        ):
            (
                available,
                _,
                sensors,
                error,
            ) = collect_robot_status(SENSORS_CONFIG)

        self.assertFalse(available)
        self.assertEqual(
            sensors.error,
            "",
        )
        self.assertEqual(
            error,
            "",
        )

    def test_suppresses_expected_grayscale_close_error(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.return_value = [
            1,
            2,
            3,
        ]
        grayscale_sensor.close.side_effect = HardwareError("close failed")

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
        ):
            result = collect_robot_status(SENSORS_CONFIG)

        self.assertTrue(result[0])
        grayscale_sensor.close.assert_called_once_with()

    def test_unexpected_grayscale_close_error_propagates(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.return_value = [
            1,
            2,
            3,
        ]
        grayscale_sensor.close.side_effect = LookupError("unexpected close failure")

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
            self.assertRaises(LookupError) as context,
        ):
            collect_robot_status(SENSORS_CONFIG)

        self.assertEqual(
            str(context.exception),
            "unexpected close failure",
        )

    def test_unexpected_grayscale_read_error_propagates(
        self,
    ) -> None:
        battery = BatteryStatus(
            available=True,
            voltage=8.2,
            state="ok",
        )
        grayscale_sensor = MagicMock()
        grayscale_sensor.read.side_effect = LookupError("unexpected read failure")

        with (
            patch(
                f"{MODULE}.collect_battery_status",
                return_value=battery,
            ),
            patch(
                f"{MODULE}.Grayscale.default",
                return_value=grayscale_sensor,
            ),
            self.assertRaises(LookupError) as context,
        ):
            collect_robot_status(SENSORS_CONFIG)

        self.assertEqual(
            str(context.exception),
            "unexpected read failure",
        )
        grayscale_sensor.close.assert_called_once_with()

    def test_rejects_invalid_config_before_battery_check(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.collect_battery_status") as collect_battery,
            patch(f"{MODULE}.Grayscale.default") as default,
            self.assertRaisesRegex(
                TypeError,
                ("sensors_config must be a SensorsConfig"),
            ),
        ):
            collect_robot_status(
                object()  # type: ignore[arg-type]
            )

        collect_battery.assert_not_called()
        default.assert_not_called()


if __name__ == "__main__":
    unittest.main()
