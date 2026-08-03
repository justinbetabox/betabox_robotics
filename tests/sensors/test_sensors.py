from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from betabox_robotics.hardware import HardwareError
from betabox_robotics.sensors import (
    Battery,
    Grayscale,
    Sensors,
    SensorsError,
    SensorsStatus,
    Ultrasonic,
)


class FakeUltrasonic(Ultrasonic):
    """Ultrasonic replacement that avoids real GPIO hardware."""

    instances: list[FakeUltrasonic] = []
    construction_error: (
        HardwareError | OSError | RuntimeError | TypeError | ValueError | None
    ) = None

    def __init__(
        self,
        config: object | None = None,
    ) -> None:
        if FakeUltrasonic.construction_error is not None:
            raise FakeUltrasonic.construction_error

        self.config = config
        self.close_count = 0
        self.close_error: HardwareError | OSError | RuntimeError | None = None
        self._closed = False

        FakeUltrasonic.instances.append(self)

    @classmethod
    def default(
        cls,
        config: object,
    ) -> FakeUltrasonic:
        return cls(config)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self.close_count += 1
        self._closed = True

        if self.close_error is not None:
            raise self.close_error


class FakeGrayscale(Grayscale):
    """Grayscale replacement that avoids real ADC hardware."""

    instances: list[FakeGrayscale] = []
    construction_error: (
        HardwareError | OSError | RuntimeError | TypeError | ValueError | None
    ) = None

    def __init__(
        self,
        config: object | None = None,
    ) -> None:
        if FakeGrayscale.construction_error is not None:
            raise FakeGrayscale.construction_error

        self.config = config
        self.close_count = 0
        self.close_error: HardwareError | OSError | RuntimeError | None = None
        self._closed = False

        FakeGrayscale.instances.append(self)

    @classmethod
    def default(
        cls,
        config: object,
    ) -> FakeGrayscale:
        return cls(config)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self.close_count += 1
        self._closed = True

        if self.close_error is not None:
            raise self.close_error


class FakeBattery(Battery):
    """Battery replacement that avoids real ADC hardware."""

    instances: list[FakeBattery] = []
    construction_error: (
        HardwareError | OSError | RuntimeError | TypeError | ValueError | None
    ) = None

    def __init__(
        self,
        config: object | None = None,
    ) -> None:
        if FakeBattery.construction_error is not None:
            raise FakeBattery.construction_error

        self.config = config
        self.close_count = 0
        self.close_error: HardwareError | OSError | RuntimeError | None = None
        self._closed = False

        FakeBattery.instances.append(self)

    @classmethod
    def default(
        cls,
        config: object,
    ) -> FakeBattery:
        return cls(config)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self.close_count += 1
        self._closed = True

        if self.close_error is not None:
            raise self.close_error


def reset_fakes() -> None:
    FakeUltrasonic.instances.clear()
    FakeUltrasonic.construction_error = None

    FakeGrayscale.instances.clear()
    FakeGrayscale.construction_error = None

    FakeBattery.instances.clear()
    FakeBattery.construction_error = None


def make_components() -> tuple[
    FakeUltrasonic,
    FakeGrayscale,
    FakeBattery,
]:
    reset_fakes()

    return (
        FakeUltrasonic(),
        FakeGrayscale(),
        FakeBattery(),
    )


def make_sensors() -> tuple[
    Sensors,
    FakeUltrasonic,
    FakeGrayscale,
    FakeBattery,
]:
    ultrasonic, grayscale, battery = make_components()

    sensors = Sensors(
        ultrasonic=ultrasonic,
        grayscale=grayscale,
        battery=battery,
    )

    return (
        sensors,
        ultrasonic,
        grayscale,
        battery,
    )


def make_config() -> SimpleNamespace:
    return SimpleNamespace(
        ultrasonic=SimpleNamespace(
            name="ultrasonic configuration",
        ),
        grayscale=SimpleNamespace(
            name="grayscale configuration",
        ),
        battery=SimpleNamespace(
            name="battery configuration",
        ),
    )


class SensorsStatusTests(unittest.TestCase):
    def test_to_dict_returns_all_fields(
        self,
    ) -> None:
        status = SensorsStatus(
            ultrasonic_closed=False,
            grayscale_closed=True,
            battery_closed=False,
            closed=True,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "ultrasonic_closed": False,
                "grayscale_closed": True,
                "battery_closed": False,
                "closed": True,
            },
        )


class SensorsConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fakes()

    def tearDown(self) -> None:
        reset_fakes()

    def test_constructor_stores_components(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        self.assertIs(
            sensors.ultrasonic,
            ultrasonic,
        )
        self.assertIs(
            sensors.grayscale,
            grayscale,
        )
        self.assertIs(
            sensors.battery,
            battery,
        )
        self.assertFalse(
            sensors.closed,
        )

    def test_constructor_requires_ultrasonic(
        self,
    ) -> None:
        _, grayscale, battery = make_components()

        with self.assertRaisesRegex(
            TypeError,
            "ultrasonic must be an Ultrasonic instance",
        ):
            Sensors(
                ultrasonic=object(),  # type: ignore[arg-type]
                grayscale=grayscale,
                battery=battery,
            )

    def test_constructor_requires_grayscale(
        self,
    ) -> None:
        ultrasonic, _, battery = make_components()

        with self.assertRaisesRegex(
            TypeError,
            "grayscale must be a Grayscale instance",
        ):
            Sensors(
                ultrasonic=ultrasonic,
                grayscale=object(),  # type: ignore[arg-type]
                battery=battery,
            )

    def test_constructor_requires_battery(
        self,
    ) -> None:
        ultrasonic, grayscale, _ = make_components()

        with self.assertRaisesRegex(
            TypeError,
            "battery must be a Battery instance",
        ):
            Sensors(
                ultrasonic=ultrasonic,
                grayscale=grayscale,
                battery=object(),  # type: ignore[arg-type]
            )


@patch(
    "betabox_robotics.sensors.sensors.Ultrasonic",
    FakeUltrasonic,
)
@patch(
    "betabox_robotics.sensors.sensors.Grayscale",
    FakeGrayscale,
)
@patch(
    "betabox_robotics.sensors.sensors.Battery",
    FakeBattery,
)
class SensorsFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fakes()

    def tearDown(self) -> None:
        reset_fakes()

    def test_default_constructs_configured_components(
        self,
    ) -> None:
        config = make_config()

        sensors = Sensors.default(
            config,
        )

        self.assertEqual(
            len(FakeUltrasonic.instances),
            1,
        )
        self.assertEqual(
            len(FakeGrayscale.instances),
            1,
        )
        self.assertEqual(
            len(FakeBattery.instances),
            1,
        )

        ultrasonic = FakeUltrasonic.instances[0]
        grayscale = FakeGrayscale.instances[0]
        battery = FakeBattery.instances[0]

        self.assertIs(
            ultrasonic.config,
            config.ultrasonic,
        )
        self.assertIs(
            grayscale.config,
            config.grayscale,
        )
        self.assertIs(
            battery.config,
            config.battery,
        )

        self.assertIs(
            sensors.ultrasonic,
            ultrasonic,
        )
        self.assertIs(
            sensors.grayscale,
            grayscale,
        )
        self.assertIs(
            sensors.battery,
            battery,
        )

    def test_default_closes_ultrasonic_when_grayscale_fails(
        self,
    ) -> None:
        config = make_config()

        error = HardwareError("grayscale construction failed")
        FakeGrayscale.construction_error = error

        with self.assertRaises(HardwareError) as raised:
            Sensors.default(
                config,
            )

        self.assertIs(
            raised.exception,
            error,
        )

        self.assertEqual(
            len(FakeUltrasonic.instances),
            1,
        )
        self.assertTrue(
            FakeUltrasonic.instances[0].closed,
        )
        self.assertEqual(
            FakeUltrasonic.instances[0].close_count,
            1,
        )

        self.assertEqual(
            FakeGrayscale.instances,
            [],
        )
        self.assertEqual(
            FakeBattery.instances,
            [],
        )

    def test_default_closes_created_components_when_battery_fails(
        self,
    ) -> None:
        config = make_config()

        error = HardwareError("battery construction failed")
        FakeBattery.construction_error = error

        with self.assertRaises(HardwareError) as raised:
            Sensors.default(
                config,
            )

        self.assertIs(
            raised.exception,
            error,
        )

        ultrasonic = FakeUltrasonic.instances[0]
        grayscale = FakeGrayscale.instances[0]

        self.assertTrue(
            ultrasonic.closed,
        )
        self.assertTrue(
            grayscale.closed,
        )
        self.assertEqual(
            ultrasonic.close_count,
            1,
        )
        self.assertEqual(
            grayscale.close_count,
            1,
        )

        self.assertEqual(
            FakeBattery.instances,
            [],
        )

    def test_default_closes_all_components_when_constructor_fails(
        self,
    ) -> None:
        config = make_config()

        with (
            patch.object(
                Sensors,
                "__init__",
                side_effect=TypeError("combined constructor failed"),
            ),
            self.assertRaisesRegex(
                TypeError,
                "combined constructor failed",
            ),
        ):
            Sensors.default(
                config,
            )

        ultrasonic = FakeUltrasonic.instances[0]
        grayscale = FakeGrayscale.instances[0]
        battery = FakeBattery.instances[0]

        self.assertTrue(
            ultrasonic.closed,
        )
        self.assertTrue(
            grayscale.closed,
        )
        self.assertTrue(
            battery.closed,
        )

    def test_default_cleanup_is_reverse_construction_order(
        self,
    ) -> None:
        config = make_config()
        close_order: list[str] = []

        original_ultrasonic_close = FakeUltrasonic.close
        original_grayscale_close = FakeGrayscale.close
        original_battery_close = FakeBattery.close

        def close_ultrasonic(
            instance: FakeUltrasonic,
        ) -> None:
            close_order.append("ultrasonic")
            original_ultrasonic_close(instance)

        def close_grayscale(
            instance: FakeGrayscale,
        ) -> None:
            close_order.append("grayscale")
            original_grayscale_close(instance)

        def close_battery(
            instance: FakeBattery,
        ) -> None:
            close_order.append("battery")
            original_battery_close(instance)

        with (
            patch.object(
                FakeUltrasonic,
                "close",
                close_ultrasonic,
            ),
            patch.object(
                FakeGrayscale,
                "close",
                close_grayscale,
            ),
            patch.object(
                FakeBattery,
                "close",
                close_battery,
            ),
            patch.object(
                Sensors,
                "__init__",
                side_effect=TypeError("combined constructor failed"),
            ),
            self.assertRaises(
                TypeError,
            ),
        ):
            Sensors.default(
                config,
            )

        self.assertEqual(
            close_order,
            [
                "battery",
                "grayscale",
                "ultrasonic",
            ],
        )

    def test_default_preserves_original_error_when_cleanup_fails(
        self,
    ) -> None:
        config = make_config()

        construction_error = HardwareError("battery construction failed")
        cleanup_error = HardwareError("grayscale cleanup failed")

        FakeBattery.construction_error = construction_error

        original_grayscale_default = FakeGrayscale.default

        def grayscale_default(
            grayscale_config: object,
        ) -> FakeGrayscale:
            grayscale = original_grayscale_default(grayscale_config)
            grayscale.close_error = cleanup_error
            return grayscale

        with (
            patch.object(
                FakeGrayscale,
                "default",
                side_effect=grayscale_default,
            ),
            self.assertRaises(HardwareError) as raised,
        ):
            Sensors.default(
                config,
            )

        self.assertIs(
            raised.exception,
            construction_error,
        )


class SensorsStatusBehaviorTests(unittest.TestCase):
    def test_status_reports_component_states(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        grayscale.close()

        self.assertEqual(
            sensors.status(),
            SensorsStatus(
                ultrasonic_closed=False,
                grayscale_closed=True,
                battery_closed=False,
                closed=False,
            ),
        )

        self.assertFalse(
            ultrasonic.closed,
        )
        self.assertTrue(
            grayscale.closed,
        )
        self.assertFalse(
            battery.closed,
        )

    def test_status_remains_available_after_close(
        self,
    ) -> None:
        sensors, _, _, _ = make_sensors()

        sensors.close()

        self.assertEqual(
            sensors.status(),
            SensorsStatus(
                ultrasonic_closed=True,
                grayscale_closed=True,
                battery_closed=True,
                closed=True,
            ),
        )


class SensorsLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fakes()

    def tearDown(self) -> None:
        reset_fakes()

    def test_close_closes_components_in_reverse_order(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        close_order: list[str] = []

        original_ultrasonic_close = ultrasonic.close
        original_grayscale_close = grayscale.close
        original_battery_close = battery.close

        def close_ultrasonic() -> None:
            close_order.append("ultrasonic")
            original_ultrasonic_close()

        def close_grayscale() -> None:
            close_order.append("grayscale")
            original_grayscale_close()

        def close_battery() -> None:
            close_order.append("battery")
            original_battery_close()

        ultrasonic.close = close_ultrasonic
        grayscale.close = close_grayscale
        battery.close = close_battery

        sensors.close()

        self.assertEqual(
            close_order,
            [
                "battery",
                "grayscale",
                "ultrasonic",
            ],
        )
        self.assertTrue(
            sensors.closed,
        )

    def test_close_closes_all_components(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        sensors.close()

        self.assertTrue(
            ultrasonic.closed,
        )
        self.assertTrue(
            grayscale.closed,
        )
        self.assertTrue(
            battery.closed,
        )
        self.assertTrue(
            sensors.closed,
        )

        self.assertEqual(
            ultrasonic.close_count,
            1,
        )
        self.assertEqual(
            grayscale.close_count,
            1,
        )
        self.assertEqual(
            battery.close_count,
            1,
        )

    def test_close_is_idempotent(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        sensors.close()
        sensors.close()

        self.assertEqual(
            ultrasonic.close_count,
            1,
        )
        self.assertEqual(
            grayscale.close_count,
            1,
        )
        self.assertEqual(
            battery.close_count,
            1,
        )

    def test_close_attempts_all_and_raises_first_error(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        battery_error = HardwareError("battery close failed")
        grayscale_error = HardwareError("grayscale close failed")
        ultrasonic_error = HardwareError("ultrasonic close failed")

        battery.close_error = battery_error
        grayscale.close_error = grayscale_error
        ultrasonic.close_error = ultrasonic_error

        with self.assertRaises(HardwareError) as raised:
            sensors.close()

        self.assertIs(
            raised.exception,
            battery_error,
        )

        self.assertEqual(
            battery.close_count,
            1,
        )
        self.assertEqual(
            grayscale.close_count,
            1,
        )
        self.assertEqual(
            ultrasonic.close_count,
            1,
        )
        self.assertTrue(
            sensors.closed,
        )

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        with sensors as entered:
            self.assertIs(
                entered,
                sensors,
            )
            self.assertFalse(
                sensors.closed,
            )

        self.assertTrue(
            ultrasonic.closed,
        )
        self.assertTrue(
            grayscale.closed,
        )
        self.assertTrue(
            battery.closed,
        )
        self.assertTrue(
            sensors.closed,
        )

    def test_closed_sensors_cannot_reenter_context(
        self,
    ) -> None:
        sensors, _, _, _ = make_sensors()
        sensors.close()

        with (
            self.assertRaisesRegex(
                SensorsError,
                "sensors subsystem is closed",
            ),
            sensors,
        ):
            pass

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        sensors, ultrasonic, grayscale, battery = make_sensors()

        sensors.deinit()

        self.assertTrue(
            ultrasonic.closed,
        )
        self.assertTrue(
            grayscale.closed,
        )
        self.assertTrue(
            battery.closed,
        )
        self.assertTrue(
            sensors.closed,
        )


if __name__ == "__main__":
    unittest.main()
