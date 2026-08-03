from __future__ import annotations

import math
import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.hardware import (
    HardwareError,
    PinMode,
    Pins,
    Pull,
)
from betabox_robotics.sensors import (
    Ultrasonic,
    UltrasonicError,
    UltrasonicReadError,
    UltrasonicTimeoutError,
)
from betabox_robotics.sensors.types import (
    UltrasonicReading,
)


class FakePin:
    """Small Pin replacement for Ultrasonic unit tests."""

    instances: list[FakePin] = []
    construction_error_at: int | None = None

    def __init__(
        self,
        pin,
        *,
        mode: PinMode = PinMode.OUT,
        pull: Pull = Pull.NONE,
        active_state: bool | None = None,
    ) -> None:
        instance_number = len(FakePin.instances)

        if FakePin.construction_error_at == instance_number:
            raise HardwareError("pin construction failed")

        self.original_pin = pin
        self.pin_number = int(pin)
        self.mode = mode
        self.pull = pull
        self.active_state = active_state

        self.closed = False
        self.output_calls = 0
        self.input_calls: list[
            tuple[
                Pull,
                bool | None,
            ]
        ] = []

        self.on_calls = 0
        self.off_calls = 0
        self.read_values: list[int] = []
        self.close_error: HardwareError | OSError | RuntimeError | None = None

        FakePin.instances.append(self)

    def output(self) -> None:
        self.output_calls += 1
        self.mode = PinMode.OUT
        self.pull = Pull.NONE
        self.active_state = None

    def input(
        self,
        pull: Pull = Pull.NONE,
        active_state: bool | None = None,
    ) -> None:
        self.input_calls.append(
            (
                pull,
                active_state,
            )
        )
        self.mode = PinMode.IN
        self.pull = pull
        self.active_state = active_state

    def on(self) -> int:
        self.on_calls += 1
        return 1

    def off(self) -> int:
        self.off_calls += 1
        return 0

    def read(self) -> int:
        if not self.read_values:
            raise AssertionError("FakePin has no queued read value")

        return self.read_values.pop(0)

    def close(self) -> None:
        self.closed = True

        if self.close_error is not None:
            raise self.close_error


def reset_fake_pins() -> None:
    FakePin.instances.clear()
    FakePin.construction_error_at = None


def make_sensor(
    *,
    trigger=Pins.D0,
    echo=Pins.D2,
    timeout: float = 0.02,
) -> tuple[
    Ultrasonic,
    FakePin,
    FakePin,
]:
    reset_fake_pins()

    sensor = Ultrasonic(
        trigger,
        echo,
        timeout=timeout,
    )

    if len(FakePin.instances) != 2:
        raise AssertionError("expected two fake pins")

    return (
        sensor,
        FakePin.instances[0],
        FakePin.instances[1],
    )


@patch(
    "betabox_robotics.sensors.ultrasonic.Pin",
    FakePin,
)
class UltrasonicConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fake_pins()

    def tearDown(self) -> None:
        reset_fake_pins()

    def test_constructs_output_and_input_pins(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        self.assertEqual(
            trigger.original_pin,
            Pins.D0,
        )
        self.assertEqual(
            trigger.mode,
            PinMode.OUT,
        )

        self.assertEqual(
            echo.original_pin,
            Pins.D2,
        )
        self.assertEqual(
            echo.mode,
            PinMode.IN,
        )
        self.assertEqual(
            echo.pull,
            Pull.DOWN,
        )

        self.assertEqual(
            trigger.off_calls,
            1,
        )
        self.assertFalse(sensor.closed)

    def test_reconfigures_injected_pin_objects(
        self,
    ) -> None:
        reset_fake_pins()

        trigger = FakePin(
            Pins.D0,
            mode=PinMode.IN,
            pull=Pull.UP,
        )
        echo = FakePin(
            Pins.D2,
            mode=PinMode.OUT,
        )

        sensor = Ultrasonic(
            trigger,
            echo,
        )

        self.assertIs(
            sensor.trigger_pin,
            trigger,
        )
        self.assertIs(
            sensor.echo_pin,
            echo,
        )

        self.assertEqual(
            trigger.output_calls,
            1,
        )
        self.assertEqual(
            echo.input_calls,
            [
                (
                    Pull.DOWN,
                    None,
                )
            ],
        )

    def test_default_uses_configuration(
        self,
    ) -> None:
        config = SimpleNamespace(
            trigger=Pins.D1,
            echo=Pins.D3,
            timeout=0.04,
        )

        sensor = Ultrasonic.default(config)

        self.assertEqual(
            sensor.trigger_pin.pin_number,
            int(Pins.D1),
        )
        self.assertEqual(
            sensor.echo_pin.pin_number,
            int(Pins.D3),
        )
        self.assertEqual(
            sensor.timeout,
            0.04,
        )

    def test_rejects_boolean_timeout(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "timeout must be a number",
        ):
            Ultrasonic(
                Pins.D0,
                Pins.D2,
                timeout=True,
            )

        self.assertEqual(
            FakePin.instances,
            [],
        )

    def test_rejects_non_numeric_timeout(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "timeout must be a number",
        ):
            Ultrasonic(
                Pins.D0,
                Pins.D2,
                timeout="fast",  # type: ignore[arg-type]
            )

    def test_rejects_non_finite_timeout(
        self,
    ) -> None:
        for timeout in (
            math.nan,
            math.inf,
            -math.inf,
        ):
            with (
                self.subTest(timeout=timeout),
                self.assertRaisesRegex(
                    ValueError,
                    "timeout must be finite",
                ),
            ):
                Ultrasonic(
                    Pins.D0,
                    Pins.D2,
                    timeout=timeout,
                )

    def test_rejects_non_positive_timeout(
        self,
    ) -> None:
        for timeout in (
            0,
            -0.01,
        ):
            with (
                self.subTest(timeout=timeout),
                self.assertRaisesRegex(
                    UltrasonicError,
                    "timeout must be greater than 0",
                ),
            ):
                Ultrasonic(
                    Pins.D0,
                    Pins.D2,
                    timeout=timeout,
                )

    def test_rejects_matching_trigger_and_echo(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            UltrasonicError,
            "trigger and echo must use different GPIO pins",
        ):
            Ultrasonic(
                Pins.D0,
                Pins.D0,
            )

        self.assertEqual(
            len(FakePin.instances),
            2,
        )
        self.assertTrue(FakePin.instances[0].closed)
        self.assertTrue(FakePin.instances[1].closed)

    def test_closes_trigger_if_echo_creation_fails(
        self,
    ) -> None:
        FakePin.construction_error_at = 1

        with self.assertRaisesRegex(
            HardwareError,
            "pin construction failed",
        ):
            Ultrasonic(
                Pins.D0,
                Pins.D2,
            )

        self.assertEqual(
            len(FakePin.instances),
            1,
        )
        self.assertTrue(FakePin.instances[0].closed)

    def test_closes_both_pins_if_trigger_initialization_fails(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        # Verify the successful-construction baseline first.
        self.assertFalse(trigger.closed)
        self.assertFalse(echo.closed)
        self.assertFalse(sensor.closed)


@patch(
    "betabox_robotics.sensors.ultrasonic.Pin",
    FakePin,
)
class UltrasonicMeasurementTests(unittest.TestCase):
    def test_read_once_generates_trigger_pulse_and_distance(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        # Wait for echo to become high, then wait for it to become low.
        echo.read_values = [
            0,
            1,
            1,
            0,
        ]

        monotonic_values = [
            0.000,
            0.001,
            0.002,
            0.002,
            0.003,
            0.004,
        ]

        with (
            patch("betabox_robotics.sensors.ultrasonic.time.sleep") as sleep_mock,
            patch(
                "betabox_robotics.sensors.ultrasonic.time.monotonic",
                side_effect=monotonic_values,
            ),
        ):
            distance = sensor._read_once()

        self.assertEqual(
            trigger.off_calls,
            3,
        )
        self.assertEqual(
            trigger.on_calls,
            1,
        )

        self.assertEqual(
            sleep_mock.call_args_list,
            [
                call(sensor.TRIGGER_SETTLE_SECONDS),
                call(sensor.TRIGGER_PULSE_SECONDS),
            ],
        )

        # 0.002 s × 343.3 m/s ÷ 2 × 100 = 34.33 cm.
        self.assertEqual(
            distance,
            34.33,
        )

    def test_read_once_times_out_waiting_for_echo_start(
        self,
    ) -> None:
        sensor, _, echo = make_sensor(timeout=0.02)

        echo.read_values = [
            0,
            0,
        ]

        with (
            patch("betabox_robotics.sensors.ultrasonic.time.sleep"),
            patch(
                "betabox_robotics.sensors.ultrasonic.time.monotonic",
                side_effect=[
                    1.00,
                    1.03,
                ],
            ),
            self.assertRaisesRegex(
                UltrasonicTimeoutError,
                "echo to start",
            ),
        ):
            sensor._read_once()

    def test_read_once_times_out_waiting_for_echo_end(
        self,
    ) -> None:
        sensor, _, echo = make_sensor(timeout=0.02)

        echo.read_values = [
            1,
            1,
            1,
        ]

        with (
            patch("betabox_robotics.sensors.ultrasonic.time.sleep"),
            patch(
                "betabox_robotics.sensors.ultrasonic.time.monotonic",
                side_effect=[
                    1.00,
                    1.01,
                    1.01,
                    1.04,
                ],
            ),
            self.assertRaisesRegex(
                UltrasonicTimeoutError,
                "echo to end",
            ),
        ):
            sensor._read_once()

    def test_read_once_rejects_non_positive_duration(
        self,
    ) -> None:
        sensor, _, echo = make_sensor()

        echo.read_values = [
            1,
            0,
        ]

        with (
            patch("betabox_robotics.sensors.ultrasonic.time.sleep"),
            patch(
                "betabox_robotics.sensors.ultrasonic.time.monotonic",
                side_effect=[
                    1.0,
                    2.0,
                    2.0,
                    2.0,
                ],
            ),
            self.assertRaisesRegex(
                UltrasonicReadError,
                "invalid ultrasonic pulse duration",
            ),
        ):
            sensor._read_once()


@patch(
    "betabox_robotics.sensors.ultrasonic.Pin",
    FakePin,
)
class UltrasonicRetryTests(unittest.TestCase):
    def test_distance_returns_first_successful_reading(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with patch.object(
            sensor,
            "_read_once",
            side_effect=[
                UltrasonicTimeoutError("first timeout"),
                UltrasonicReadError("invalid pulse"),
                42.5,
            ],
        ) as read_once:
            result = sensor.distance(samples=5)

        self.assertEqual(
            result,
            42.5,
        )
        self.assertEqual(
            read_once.call_count,
            3,
        )

    def test_distance_raises_timeout_after_all_attempts(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        original_error = UltrasonicTimeoutError("echo timeout")

        with (
            patch.object(
                sensor,
                "_read_once",
                side_effect=original_error,
            ) as read_once,
            self.assertRaisesRegex(
                UltrasonicTimeoutError,
                "after 3 attempts",
            ) as raised,
        ):
            sensor.distance(samples=3)

        self.assertEqual(
            read_once.call_count,
            3,
        )
        self.assertIs(
            raised.exception.__cause__,
            original_error,
        )

    def test_distance_raises_read_error_when_last_failure_is_invalid(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        last_error = UltrasonicReadError("invalid duration")

        with (
            patch.object(
                sensor,
                "_read_once",
                side_effect=[
                    UltrasonicTimeoutError("timeout"),
                    last_error,
                ],
            ),
            self.assertRaisesRegex(
                UltrasonicReadError,
                "after 2 attempts",
            ) as raised,
        ):
            sensor.distance(samples=2)

        self.assertIs(
            raised.exception.__cause__,
            last_error,
        )

    def test_distance_does_not_retry_unrelated_hardware_error(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with (
            patch.object(
                sensor,
                "_read_once",
                side_effect=HardwareError("GPIO failure"),
            ) as read_once,
            self.assertRaisesRegex(
                HardwareError,
                "GPIO failure",
            ),
        ):
            sensor.distance(samples=5)

        read_once.assert_called_once_with()

    def test_distance_rejects_boolean_samples(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with self.assertRaisesRegex(
            TypeError,
            "samples must be an integer",
        ):
            sensor.distance(samples=True)

    def test_distance_rejects_non_integer_samples(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with self.assertRaisesRegex(
            TypeError,
            "samples must be an integer",
        ):
            sensor.distance(
                samples=2.5  # type: ignore[arg-type]
            )

    def test_distance_rejects_non_positive_samples(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        for samples in (
            0,
            -1,
        ):
            with (
                self.subTest(samples=samples),
                self.assertRaisesRegex(
                    UltrasonicError,
                    "samples must be greater than 0",
                ),
            ):
                sensor.distance(samples=samples)


@patch(
    "betabox_robotics.sensors.ultrasonic.Pin",
    FakePin,
)
class UltrasonicCompatibilityTests(unittest.TestCase):
    def test_read_returns_distance(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with patch.object(
            sensor,
            "distance",
            return_value=28.75,
        ) as distance:
            result = sensor.read(times=4)

        self.assertEqual(
            result,
            28.75,
        )
        distance.assert_called_once_with(samples=4)

    def test_read_returns_minus_one_for_timeout(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with patch.object(
            sensor,
            "distance",
            side_effect=UltrasonicTimeoutError("timeout"),
        ):
            self.assertEqual(
                sensor.read(),
                -1,
            )

    def test_read_returns_minus_two_for_invalid_reading(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with patch.object(
            sensor,
            "distance",
            side_effect=UltrasonicReadError("invalid pulse"),
        ):
            self.assertEqual(
                sensor.read(),
                -2,
            )

    def test_read_does_not_hide_other_errors(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with (
            patch.object(
                sensor,
                "distance",
                side_effect=HardwareError("GPIO failed"),
            ),
            self.assertRaisesRegex(
                HardwareError,
                "GPIO failed",
            ),
        ):
            sensor.read()


@patch(
    "betabox_robotics.sensors.ultrasonic.Pin",
    FakePin,
)
class UltrasonicReadingTests(unittest.TestCase):
    def test_reading_returns_structured_value(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with patch.object(
            sensor,
            "distance",
            return_value=31.25,
        ) as distance:
            reading = sensor.reading(samples=6)

        self.assertEqual(
            reading,
            UltrasonicReading(
                distance_cm=31.25,
                samples_requested=6,
            ),
        )

        distance.assert_called_once_with(samples=6)

    def test_reading_validates_samples_before_reading(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()

        with (
            patch.object(
                sensor,
                "distance",
            ) as distance,
            self.assertRaisesRegex(
                TypeError,
                "samples must be an integer",
            ),
        ):
            sensor.reading(samples=True)

        distance.assert_not_called()


@patch(
    "betabox_robotics.sensors.ultrasonic.Pin",
    FakePin,
)
class UltrasonicLifecycleTests(unittest.TestCase):
    def test_close_closes_echo_then_trigger(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        close_order: list[str] = []

        original_trigger_close = trigger.close
        original_echo_close = echo.close

        def close_trigger() -> None:
            close_order.append("trigger")
            original_trigger_close()

        def close_echo() -> None:
            close_order.append("echo")
            original_echo_close()

        trigger.close = close_trigger
        echo.close = close_echo

        sensor.close()

        self.assertEqual(
            close_order,
            [
                "echo",
                "trigger",
            ],
        )
        self.assertTrue(trigger.closed)
        self.assertTrue(echo.closed)
        self.assertTrue(sensor.closed)

    def test_close_is_idempotent(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        sensor.close()
        sensor.close()

        self.assertTrue(trigger.closed)
        self.assertTrue(echo.closed)
        self.assertTrue(sensor.closed)

    def test_close_attempts_both_and_raises_first_error(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        echo_error = HardwareError("echo close failed")
        trigger_error = HardwareError("trigger close failed")

        echo.close_error = echo_error
        trigger.close_error = trigger_error

        with self.assertRaises(HardwareError) as raised:
            sensor.close()

        self.assertIs(
            raised.exception,
            echo_error,
        )
        self.assertTrue(echo.closed)
        self.assertTrue(trigger.closed)
        self.assertTrue(sensor.closed)

    def test_closed_sensor_rejects_measurements(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()
        sensor.close()

        operations = (
            lambda: sensor.distance(),
            lambda: sensor._read_once(),
        )

        for operation in operations:
            with (
                self.subTest(operation=operation),
                self.assertRaisesRegex(
                    UltrasonicError,
                    "ultrasonic sensor is closed",
                ),
            ):
                operation()

    def test_closed_pin_properties_raise(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()
        sensor.close()

        with self.assertRaisesRegex(
            UltrasonicError,
            "trigger pin is closed",
        ):
            _ = sensor.trigger_pin

        with self.assertRaisesRegex(
            UltrasonicError,
            "echo pin is closed",
        ):
            _ = sensor.echo_pin

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        with sensor as entered:
            self.assertIs(
                entered,
                sensor,
            )
            self.assertFalse(sensor.closed)

        self.assertTrue(trigger.closed)
        self.assertTrue(echo.closed)
        self.assertTrue(sensor.closed)

    def test_closed_sensor_cannot_reenter_context(
        self,
    ) -> None:
        sensor, _, _ = make_sensor()
        sensor.close()

        with (
            self.assertRaisesRegex(
                UltrasonicError,
                "ultrasonic sensor is closed",
            ),
            sensor,
        ):
            pass

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        sensor, trigger, echo = make_sensor()

        sensor.deinit()

        self.assertTrue(trigger.closed)
        self.assertTrue(echo.closed)
        self.assertTrue(sensor.closed)


if __name__ == "__main__":
    unittest.main()
