from __future__ import annotations

import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from betabox_robotics.hardware import (
    ADC,
    HardwareError,
    Pins,
)
from betabox_robotics.sensors import (
    Battery,
    BatteryError,
)
from betabox_robotics.sensors.types import (
    BatteryReading,
    BatteryState,
)


class FakeADC(ADC):
    """ADC replacement that avoids real I²C hardware."""

    instances: list[FakeADC] = []
    construction_error: HardwareError | OSError | RuntimeError | None = None

    def __init__(
        self,
        channel,
        *args,
        **kwargs,
    ) -> None:
        if FakeADC.construction_error is not None:
            raise FakeADC.construction_error

        # Do not call ADC.__init__(); it would open real hardware.
        self.channel = channel
        self.voltage_value: object = 0.0

        self.read_error: (
            HardwareError | OSError | RuntimeError | TypeError | ValueError | None
        ) = None

        self.close_error: HardwareError | OSError | RuntimeError | None = None

        self.read_voltage_count = 0
        self.close_count = 0
        self._closed = False

        FakeADC.instances.append(self)

    @property
    def closed(self) -> bool:
        return self._closed

    def read_voltage(self) -> float:
        self.read_voltage_count += 1

        if self.read_error is not None:
            raise self.read_error

        if self._closed:
            raise HardwareError("ADC is closed")

        return self.voltage_value  # type: ignore[return-value]

    def close(self) -> None:
        self.close_count += 1
        self._closed = True

        if self.close_error is not None:
            raise self.close_error


def reset_fake_adcs() -> None:
    FakeADC.instances.clear()
    FakeADC.construction_error = None


def make_adc(
    *,
    voltage: object = 2.5,
) -> FakeADC:
    adc = FakeADC(Pins.A4)
    adc.voltage_value = voltage
    return adc


def make_battery(
    *,
    measured_voltage: object = 2.5,
    scale: float = 3.0,
    low_voltage: float = 6.6,
    critical_voltage: float = 6.2,
) -> tuple[
    Battery,
    FakeADC,
]:
    reset_fake_adcs()

    adc = make_adc(
        voltage=measured_voltage,
    )

    battery = Battery(
        adc,
        scale=scale,
        low_voltage=low_voltage,
        critical_voltage=critical_voltage,
    )

    return battery, adc


class BatteryConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fake_adcs()

    def tearDown(self) -> None:
        reset_fake_adcs()

    def test_constructor_stores_configuration(
        self,
    ) -> None:
        adc = make_adc()

        battery = Battery(
            adc,
            scale=3.2,
            low_voltage=6.8,
            critical_voltage=6.3,
        )

        self.assertIs(
            battery.adc,
            adc,
        )
        self.assertEqual(
            battery.scale,
            3.2,
        )
        self.assertEqual(
            battery.low_voltage,
            6.8,
        )
        self.assertEqual(
            battery.critical_voltage,
            6.3,
        )
        self.assertFalse(
            battery.closed,
        )

    def test_constructor_requires_adc(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "adc must be an ADC instance",
        ):
            Battery(
                object(),  # type: ignore[arg-type]
            )

    def test_rejects_boolean_numeric_configuration(
        self,
    ) -> None:
        cases = (
            (
                {
                    "scale": True,
                },
                "scale must be a number",
            ),
            (
                {
                    "low_voltage": True,
                },
                "low_voltage must be a number",
            ),
            (
                {
                    "critical_voltage": True,
                },
                "critical_voltage must be a number",
            ),
        )

        for kwargs, message in cases:
            with (
                self.subTest(
                    kwargs=kwargs,
                ),
                self.assertRaisesRegex(
                    TypeError,
                    message,
                ),
            ):
                Battery(
                    make_adc(),
                    **kwargs,  # type: ignore[arg-type]
                )

    def test_rejects_non_numeric_configuration(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "scale must be a number",
        ):
            Battery(
                make_adc(),
                scale="three",  # type: ignore[arg-type]
            )

    def test_rejects_non_finite_configuration(
        self,
    ) -> None:
        cases = (
            (
                {
                    "scale": math.nan,
                },
                "scale must be finite",
            ),
            (
                {
                    "low_voltage": math.inf,
                },
                "low_voltage must be finite",
            ),
            (
                {
                    "critical_voltage": -math.inf,
                },
                "critical_voltage must be finite",
            ),
        )

        for kwargs, message in cases:
            with (
                self.subTest(
                    kwargs=kwargs,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    message,
                ),
            ):
                Battery(
                    make_adc(),
                    **kwargs,
                )

    def test_rejects_non_positive_scale(
        self,
    ) -> None:
        for scale in (
            0,
            -1,
        ):
            with (
                self.subTest(
                    scale=scale,
                ),
                self.assertRaisesRegex(
                    BatteryError,
                    "scale must be greater than 0",
                ),
            ):
                Battery(
                    make_adc(),
                    scale=scale,
                )

    def test_rejects_non_positive_critical_voltage(
        self,
    ) -> None:
        for critical_voltage in (
            0,
            -1,
        ):
            with (
                self.subTest(
                    critical_voltage=critical_voltage,
                ),
                self.assertRaisesRegex(
                    BatteryError,
                    "critical_voltage must be greater than 0",
                ),
            ):
                Battery(
                    make_adc(),
                    critical_voltage=critical_voltage,
                )

    def test_requires_low_voltage_above_critical_voltage(
        self,
    ) -> None:
        for low_voltage in (
            6.2,
            6.1,
        ):
            with (
                self.subTest(
                    low_voltage=low_voltage,
                ),
                self.assertRaisesRegex(
                    BatteryError,
                    "low_voltage must be greater than critical_voltage",
                ),
            ):
                Battery(
                    make_adc(),
                    low_voltage=low_voltage,
                    critical_voltage=6.2,
                )


@patch(
    "betabox_robotics.sensors.battery.ADC",
    FakeADC,
)
class BatteryFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fake_adcs()

    def tearDown(self) -> None:
        reset_fake_adcs()

    def test_default_constructs_configured_battery(
        self,
    ) -> None:
        config = SimpleNamespace(
            channel=Pins.A4,
            scale=3.1,
            low_voltage=6.7,
            critical_voltage=6.3,
        )

        battery = Battery.default(
            config,
        )

        self.assertEqual(
            len(FakeADC.instances),
            1,
        )
        self.assertEqual(
            FakeADC.instances[0].channel,
            Pins.A4,
        )
        self.assertIs(
            battery.adc,
            FakeADC.instances[0],
        )
        self.assertEqual(
            battery.scale,
            3.1,
        )
        self.assertEqual(
            battery.low_voltage,
            6.7,
        )
        self.assertEqual(
            battery.critical_voltage,
            6.3,
        )

    def test_default_propagates_adc_construction_error(
        self,
    ) -> None:
        error = HardwareError("ADC construction failed")
        FakeADC.construction_error = error

        config = SimpleNamespace(
            channel=Pins.A4,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        with self.assertRaises(HardwareError) as raised:
            Battery.default(
                config,
            )

        self.assertIs(
            raised.exception,
            error,
        )
        self.assertEqual(
            FakeADC.instances,
            [],
        )

    def test_default_closes_adc_when_battery_validation_fails(
        self,
    ) -> None:
        config = SimpleNamespace(
            channel=Pins.A4,
            scale=0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        with self.assertRaisesRegex(
            BatteryError,
            "scale must be greater than 0",
        ):
            Battery.default(
                config,
            )

        self.assertEqual(
            len(FakeADC.instances),
            1,
        )
        self.assertTrue(
            FakeADC.instances[0].closed,
        )
        self.assertEqual(
            FakeADC.instances[0].close_count,
            1,
        )


class BatteryVoltageTests(unittest.TestCase):
    def test_voltage_scales_and_rounds_adc_voltage(
        self,
    ) -> None:
        battery, adc = make_battery(
            measured_voltage=2.734,
            scale=3.0,
        )

        self.assertEqual(
            battery.voltage(),
            8.2,
        )
        self.assertEqual(
            adc.read_voltage_count,
            1,
        )

    def test_read_is_compatibility_alias(
        self,
    ) -> None:
        battery, adc = make_battery(
            measured_voltage=2.5,
            scale=3.0,
        )

        self.assertEqual(
            battery.read(),
            7.5,
        )
        self.assertEqual(
            adc.read_voltage_count,
            1,
        )

    def test_voltage_wraps_adc_hardware_error(
        self,
    ) -> None:
        battery, adc = make_battery()

        error = HardwareError("ADC read failed")
        adc.read_error = error

        with self.assertRaisesRegex(
            BatteryError,
            "failed to read battery voltage",
        ) as raised:
            battery.voltage()

        self.assertIs(
            raised.exception.__cause__,
            error,
        )

    def test_voltage_wraps_invalid_adc_type(
        self,
    ) -> None:
        battery, adc = make_battery(
            measured_voltage="invalid",
        )

        with self.assertRaisesRegex(
            BatteryError,
            "failed to read battery voltage",
        ) as raised:
            battery.voltage()

        self.assertIsInstance(
            raised.exception.__cause__,
            TypeError,
        )
        self.assertEqual(
            adc.read_voltage_count,
            1,
        )

    def test_voltage_rejects_non_finite_adc_value(
        self,
    ) -> None:
        for measured_voltage in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            battery, _ = make_battery(
                measured_voltage=measured_voltage,
            )

            with (
                self.subTest(
                    measured_voltage=measured_voltage,
                ),
                self.assertRaisesRegex(
                    BatteryError,
                    "failed to read battery voltage",
                ) as raised,
            ):
                battery.voltage()

            self.assertIsInstance(
                raised.exception.__cause__,
                ValueError,
            )

    def test_voltage_rejects_negative_adc_value(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=-0.1,
        )

        with self.assertRaisesRegex(
            BatteryError,
            "ADC voltage cannot be negative",
        ) as raised:
            battery.voltage()

        self.assertIsNone(
            raised.exception.__cause__,
        )

    def test_voltage_rejects_non_finite_scaled_result(
        self,
    ) -> None:
        battery, adc = make_battery()
        adc.voltage_value = 1e308
        battery.scale = 1e308

        with self.assertRaisesRegex(
            BatteryError,
            "calculated battery voltage is not finite",
        ):
            battery.voltage()


class BatteryStateTests(unittest.TestCase):
    def test_state_is_ok_above_low_threshold(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.21,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        self.assertIs(
            battery.status(),
            BatteryState.OK,
        )

    def test_state_is_low_at_low_threshold(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.2,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        self.assertIs(
            battery.status(),
            BatteryState.LOW,
        )

    def test_state_is_low_between_thresholds(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.1,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        self.assertIs(
            battery.status(),
            BatteryState.LOW,
        )

    def test_state_is_critical_at_critical_threshold(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=6.2 / 3.0,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        self.assertIs(
            battery.status(),
            BatteryState.CRITICAL,
        )

    def test_state_is_critical_below_threshold(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.0,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        self.assertIs(
            battery.status(),
            BatteryState.CRITICAL,
        )

    def test_reading_returns_voltage_and_state(
        self,
    ) -> None:
        battery, adc = make_battery(
            measured_voltage=2.1,
            scale=3.0,
            low_voltage=6.6,
            critical_voltage=6.2,
        )

        self.assertEqual(
            battery.reading(),
            BatteryReading(
                voltage=6.3,
                state=BatteryState.LOW,
            ),
        )

        self.assertEqual(
            adc.read_voltage_count,
            1,
        )

    def test_is_low_uses_reading_state(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.1,
        )

        self.assertTrue(
            battery.is_low(),
        )

    def test_is_low_is_true_for_critical_state(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.0,
        )

        self.assertTrue(
            battery.is_low(),
        )

    def test_is_critical_reports_critical_state(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.0,
        )

        self.assertTrue(
            battery.is_critical(),
        )

    def test_is_critical_is_false_for_low_state(
        self,
    ) -> None:
        battery, _ = make_battery(
            measured_voltage=2.1,
        )

        self.assertFalse(
            battery.is_critical(),
        )


class BatteryLifecycleTests(unittest.TestCase):
    def test_close_closes_adc(
        self,
    ) -> None:
        battery, adc = make_battery()

        battery.close()

        self.assertTrue(
            battery.closed,
        )
        self.assertTrue(
            adc.closed,
        )
        self.assertEqual(
            adc.close_count,
            1,
        )

    def test_close_is_idempotent(
        self,
    ) -> None:
        battery, adc = make_battery()

        battery.close()
        battery.close()

        self.assertTrue(
            battery.closed,
        )
        self.assertEqual(
            adc.close_count,
            1,
        )

    def test_close_marks_battery_closed_when_adc_close_fails(
        self,
    ) -> None:
        battery, adc = make_battery()

        error = HardwareError("ADC close failed")
        adc.close_error = error

        with self.assertRaises(HardwareError) as raised:
            battery.close()

        self.assertIs(
            raised.exception,
            error,
        )
        self.assertTrue(
            battery.closed,
        )
        self.assertTrue(
            adc.closed,
        )

    def test_closed_battery_rejects_read_operations(
        self,
    ) -> None:
        battery, _ = make_battery()
        battery.close()

        operations = (
            lambda: battery.voltage(),
            lambda: battery.read(),
            lambda: battery.status(),
            lambda: battery.reading(),
            lambda: battery.is_low(),
            lambda: battery.is_critical(),
        )

        for operation in operations:
            with (
                self.subTest(
                    operation=operation,
                ),
                self.assertRaisesRegex(
                    BatteryError,
                    "battery sensor is closed",
                ),
            ):
                operation()

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        battery, adc = make_battery()

        with battery as entered:
            self.assertIs(
                entered,
                battery,
            )
            self.assertFalse(
                battery.closed,
            )

        self.assertTrue(
            battery.closed,
        )
        self.assertTrue(
            adc.closed,
        )

    def test_closed_battery_cannot_reenter_context(
        self,
    ) -> None:
        battery, _ = make_battery()
        battery.close()

        with (
            self.assertRaisesRegex(
                BatteryError,
                "battery sensor is closed",
            ),
            battery,
        ):
            pass

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        battery, adc = make_battery()

        battery.deinit()

        self.assertTrue(
            battery.closed,
        )
        self.assertTrue(
            adc.closed,
        )
        self.assertEqual(
            adc.close_count,
            1,
        )


if __name__ == "__main__":
    unittest.main()
