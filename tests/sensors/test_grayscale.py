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
    Grayscale,
    GrayscaleError,
)
from betabox_robotics.sensors.types import (
    GrayscaleReading,
)


class FakeADC(ADC):
    """ADC replacement that does not access real I²C hardware."""

    instances: list[FakeADC] = []
    construction_error_at: int | None = None

    def __init__(
        self,
        channel,
        *args,
        **kwargs,
    ) -> None:
        instance_number = len(FakeADC.instances)

        if FakeADC.construction_error_at == instance_number:
            raise HardwareError("ADC construction failed")

        # Do not call ADC.__init__(), because that would open
        # the real SMBus/I²C hardware.
        self.channel = channel
        self.read_value = 0

        self.read_error: HardwareError | OSError | RuntimeError | None = None

        self.close_error: HardwareError | OSError | RuntimeError | None = None

        self.read_count = 0
        self.close_count = 0
        self._closed = False

        FakeADC.instances.append(self)

    @property
    def closed(self) -> bool:
        return self._closed

    def read(self) -> int:
        self.read_count += 1

        if self.read_error is not None:
            raise self.read_error

        if self._closed:
            raise HardwareError("ADC is closed")

        return self.read_value

    def close(self) -> None:
        self.close_count += 1
        self._closed = True

        if self.close_error is not None:
            raise self.close_error


def reset_fake_adcs() -> None:
    FakeADC.instances.clear()
    FakeADC.construction_error_at = None


def make_adc(
    channel,
    *,
    value: int = 0,
) -> FakeADC:
    adc = FakeADC(channel)
    adc.read_value = value
    return adc


def make_grayscale(
    *,
    left_value: int = 1000,
    middle_value: int = 1000,
    right_value: int = 1000,
    reference: tuple[int, int, int] | None = None,
) -> tuple[
    Grayscale,
    FakeADC,
    FakeADC,
    FakeADC,
]:
    reset_fake_adcs()

    left = make_adc(
        Pins.A0,
        value=left_value,
    )
    middle = make_adc(
        Pins.A1,
        value=middle_value,
    )
    right = make_adc(
        Pins.A2,
        value=right_value,
    )

    grayscale = Grayscale(
        left,
        middle,
        right,
        reference=reference,
    )

    return (
        grayscale,
        left,
        middle,
        right,
    )


class GrayscaleConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fake_adcs()

    def tearDown(self) -> None:
        reset_fake_adcs()

    def test_constructor_stores_channels_in_order(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale()

        self.assertEqual(
            grayscale.channels,
            (
                left,
                middle,
                right,
            ),
        )
        self.assertFalse(grayscale.closed)

    def test_constructor_uses_default_reference(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        self.assertEqual(
            grayscale.reference(),
            [
                1000,
                1000,
                1000,
            ],
        )

    def test_constructor_uses_custom_reference(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale(
            reference=(
                800,
                900,
                1000,
            )
        )

        self.assertEqual(
            grayscale.reference(),
            [
                800,
                900,
                1000,
            ],
        )

    def test_constructor_requires_left_adc(
        self,
    ) -> None:
        middle = make_adc(Pins.A1)
        right = make_adc(Pins.A2)

        with self.assertRaisesRegex(
            TypeError,
            "left must be an ADC instance",
        ):
            Grayscale(
                object(),  # type: ignore[arg-type]
                middle,
                right,
            )

    def test_constructor_requires_middle_adc(
        self,
    ) -> None:
        left = make_adc(Pins.A0)
        right = make_adc(Pins.A2)

        with self.assertRaisesRegex(
            TypeError,
            "middle must be an ADC instance",
        ):
            Grayscale(
                left,
                object(),  # type: ignore[arg-type]
                right,
            )

    def test_constructor_requires_right_adc(
        self,
    ) -> None:
        left = make_adc(Pins.A0)
        middle = make_adc(Pins.A1)

        with self.assertRaisesRegex(
            TypeError,
            "right must be an ADC instance",
        ):
            Grayscale(
                left,
                middle,
                object(),  # type: ignore[arg-type]
            )

    def test_reference_requires_three_values(
        self,
    ) -> None:
        left = make_adc(Pins.A0)
        middle = make_adc(Pins.A1)
        right = make_adc(Pins.A2)

        with self.assertRaisesRegex(
            GrayscaleError,
            "reference values must contain 3 values",
        ):
            Grayscale(
                left,
                middle,
                right,
                reference=(
                    1000,
                    1000,
                ),
            )

    def test_reference_rejects_string_sequence(
        self,
    ) -> None:
        left = make_adc(Pins.A0)
        middle = make_adc(Pins.A1)
        right = make_adc(Pins.A2)

        with self.assertRaisesRegex(
            TypeError,
            "reference values must be a sequence of integers",
        ):
            Grayscale(
                left,
                middle,
                right,
                reference="123",  # type: ignore[arg-type]
            )

    def test_reference_rejects_boolean_value(
        self,
    ) -> None:
        left = make_adc(Pins.A0)
        middle = make_adc(Pins.A1)
        right = make_adc(Pins.A2)

        with self.assertRaisesRegex(
            TypeError,
            "reference value 1 must be an integer",
        ):
            Grayscale(
                left,
                middle,
                right,
                reference=(
                    1000,
                    True,
                    1000,
                ),
            )

    def test_reference_rejects_value_outside_adc_range(
        self,
    ) -> None:
        left = make_adc(Pins.A0)
        middle = make_adc(Pins.A1)
        right = make_adc(Pins.A2)

        with self.assertRaisesRegex(
            GrayscaleError,
            "reference value 2 must be between",
        ):
            Grayscale(
                left,
                middle,
                right,
                reference=(
                    1000,
                    1000,
                    ADC.MAX_VALUE + 1,
                ),
            )


@patch(
    "betabox_robotics.sensors.grayscale.ADC",
    FakeADC,
)
class GrayscaleFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fake_adcs()

    def tearDown(self) -> None:
        reset_fake_adcs()

    def test_default_constructs_configured_channels(
        self,
    ) -> None:
        config = SimpleNamespace(
            left=Pins.A0,
            middle=Pins.A1,
            right=Pins.A2,
            reference=(
                700,
                800,
                900,
            ),
        )

        grayscale = Grayscale.default(config)

        self.assertEqual(
            [adc.channel for adc in FakeADC.instances],
            [
                Pins.A0,
                Pins.A1,
                Pins.A2,
            ],
        )

        self.assertEqual(
            grayscale.reference(),
            [
                700,
                800,
                900,
            ],
        )

    def test_default_closes_left_when_middle_creation_fails(
        self,
    ) -> None:
        config = SimpleNamespace(
            left=Pins.A0,
            middle=Pins.A1,
            right=Pins.A2,
            reference=None,
        )

        FakeADC.construction_error_at = 1

        with self.assertRaisesRegex(
            HardwareError,
            "ADC construction failed",
        ):
            Grayscale.default(config)

        self.assertEqual(
            len(FakeADC.instances),
            1,
        )
        self.assertTrue(FakeADC.instances[0].closed)

    def test_default_closes_created_channels_when_right_creation_fails(
        self,
    ) -> None:
        config = SimpleNamespace(
            left=Pins.A0,
            middle=Pins.A1,
            right=Pins.A2,
            reference=None,
        )

        FakeADC.construction_error_at = 2

        with self.assertRaisesRegex(
            HardwareError,
            "ADC construction failed",
        ):
            Grayscale.default(config)

        self.assertEqual(
            len(FakeADC.instances),
            2,
        )
        self.assertTrue(FakeADC.instances[0].closed)
        self.assertTrue(FakeADC.instances[1].closed)

    def test_default_closes_all_channels_when_constructor_validation_fails(
        self,
    ) -> None:
        config = SimpleNamespace(
            left=Pins.A0,
            middle=Pins.A1,
            right=Pins.A2,
            reference=(
                1000,
                True,
                1000,
            ),
        )

        with self.assertRaisesRegex(
            TypeError,
            "reference value 1 must be an integer",
        ):
            Grayscale.default(config)

        self.assertEqual(
            len(FakeADC.instances),
            3,
        )

        self.assertTrue(all(adc.closed for adc in FakeADC.instances))


class GrayscaleReadTests(unittest.TestCase):
    def test_read_returns_all_channels(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale(
            left_value=100,
            middle_value=200,
            right_value=300,
        )

        self.assertEqual(
            grayscale.read(),
            [
                100,
                200,
                300,
            ],
        )

        self.assertEqual(
            left.read_count,
            1,
        )
        self.assertEqual(
            middle.read_count,
            1,
        )
        self.assertEqual(
            right.read_count,
            1,
        )

    def test_read_returns_selected_channel(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale(
            left_value=100,
            middle_value=200,
            right_value=300,
        )

        self.assertEqual(
            grayscale.read(Grayscale.MIDDLE),
            [
                200,
            ],
        )

        self.assertEqual(
            left.read_count,
            0,
        )
        self.assertEqual(
            middle.read_count,
            1,
        )
        self.assertEqual(
            right.read_count,
            0,
        )

    def test_read_rejects_boolean_channel(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            TypeError,
            "channel must be an integer",
        ):
            grayscale.read(True)

    def test_read_rejects_non_integer_channel(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            TypeError,
            "channel must be an integer",
        ):
            grayscale.read(
                1.5  # type: ignore[arg-type]
            )

    def test_read_rejects_invalid_channel(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            GrayscaleError,
            "channel must be Grayscale.LEFT",
        ):
            grayscale.read(3)

    def test_read_wraps_adc_hardware_error(
        self,
    ) -> None:
        grayscale, _, middle, _ = make_grayscale()

        error = HardwareError("ADC read failed")
        middle.read_error = error

        with self.assertRaisesRegex(
            GrayscaleError,
            "failed to read grayscale sensor",
        ) as raised:
            grayscale.read()

        self.assertIs(
            raised.exception.__cause__,
            error,
        )

    def test_read_does_not_wrap_validation_error(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaises(GrayscaleError) as raised:
            grayscale.read(99)

        self.assertIsNone(raised.exception.__cause__)


class GrayscaleReferenceTests(unittest.TestCase):
    def test_reference_returns_copy(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        result = grayscale.reference()
        result[0] = 50

        self.assertEqual(
            grayscale.reference(),
            [
                1000,
                1000,
                1000,
            ],
        )

    def test_reference_updates_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        result = grayscale.reference(
            (
                700,
                800,
                900,
            )
        )

        self.assertEqual(
            result,
            [
                700,
                800,
                900,
            ],
        )

        self.assertEqual(
            grayscale.reference(),
            [
                700,
                800,
                900,
            ],
        )

    def test_reference_update_uses_same_validation(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            TypeError,
            "reference value 0 must be an integer",
        ):
            grayscale.reference(
                (
                    1.2,
                    800,
                    900,
                )  # type: ignore[arg-type]
            )


class GrayscaleCalibrationTests(unittest.TestCase):
    def test_initial_calibration_is_unset(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        self.assertEqual(
            grayscale.get_calibration(),
            (
                None,
                None,
            ),
        )

    def test_set_calibration_stores_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        grayscale.set_calibration(
            floor=(
                3000,
                3100,
                3200,
            ),
            line=(
                500,
                600,
                700,
            ),
        )

        self.assertEqual(
            grayscale.get_calibration(),
            (
                (
                    3000.0,
                    3100.0,
                    3200.0,
                ),
                (
                    500.0,
                    600.0,
                    700.0,
                ),
            ),
        )

    def test_set_calibration_requires_three_floor_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            GrayscaleError,
            "floor must contain 3 values",
        ):
            grayscale.set_calibration(
                floor=(
                    100,
                    200,
                ),
                line=(
                    900,
                    900,
                    900,
                ),
            )

    def test_set_calibration_requires_three_line_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            GrayscaleError,
            "line must contain 3 values",
        ):
            grayscale.set_calibration(
                floor=(
                    100,
                    100,
                    100,
                ),
                line=(
                    900,
                    900,
                ),
            )

    def test_set_calibration_rejects_non_numeric_value(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            TypeError,
            r"floor\[1\] must be a number",
        ):
            grayscale.set_calibration(
                floor=(
                    100,
                    "dark",  # type: ignore[arg-type]
                    100,
                ),
                line=(
                    900,
                    900,
                    900,
                ),
            )

    def test_set_calibration_rejects_non_finite_value(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            ValueError,
            r"line\[2\] must be finite",
        ):
            grayscale.set_calibration(
                floor=(
                    100,
                    100,
                    100,
                ),
                line=(
                    900,
                    900,
                    math.nan,
                ),
            )

    def test_set_calibration_rejects_equal_floor_and_line(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            GrayscaleError,
            "must differ for channel 1",
        ):
            grayscale.set_calibration(
                floor=(
                    100,
                    500,
                    100,
                ),
                line=(
                    900,
                    500,
                    900,
                ),
            )

    def test_failed_calibration_does_not_replace_previous_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        with self.assertRaises(GrayscaleError):
            grayscale.set_calibration(
                floor=(
                    100,
                    500,
                    100,
                ),
                line=(
                    900,
                    500,
                    900,
                ),
            )

        self.assertEqual(
            grayscale.get_calibration(),
            (
                (
                    100.0,
                    100.0,
                    100.0,
                ),
                (
                    900.0,
                    900.0,
                    900.0,
                ),
            ),
        )


class GrayscaleNormalizationTests(unittest.TestCase):
    def test_normalized_requires_calibration(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            GrayscaleError,
            "calibration not set",
        ):
            grayscale.normalized(
                (
                    100,
                    200,
                    300,
                )
            )

    def test_normalizes_when_line_value_is_higher(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        self.assertEqual(
            grayscale.normalized(
                (
                    100,
                    500,
                    900,
                )
            ),
            [
                0.0,
                0.5,
                1.0,
            ],
        )

    def test_normalizes_when_line_value_is_lower(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        grayscale.set_calibration(
            floor=(
                900,
                900,
                900,
            ),
            line=(
                100,
                100,
                100,
            ),
        )

        self.assertEqual(
            grayscale.normalized(
                (
                    900,
                    500,
                    100,
                )
            ),
            [
                0.0,
                0.5,
                1.0,
            ],
        )

    def test_normalized_clamps_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        self.assertEqual(
            grayscale.normalized(
                (
                    -100,
                    500,
                    1200,
                )
            ),
            [
                0.0,
                0.5,
                1.0,
            ],
        )

    def test_normalized_reads_hardware_when_raw_is_omitted(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale(
            left_value=100,
            middle_value=500,
            right_value=900,
        )

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        self.assertEqual(
            grayscale.normalized(),
            [
                0.0,
                0.5,
                1.0,
            ],
        )

        self.assertEqual(
            left.read_count,
            1,
        )
        self.assertEqual(
            middle.read_count,
            1,
        )
        self.assertEqual(
            right.read_count,
            1,
        )

    def test_normalized_requires_three_raw_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        with self.assertRaisesRegex(
            GrayscaleError,
            "raw values must contain 3 values",
        ):
            grayscale.normalized(
                (
                    100,
                    200,
                )
            )


class GrayscaleStatusTests(unittest.TestCase):
    def test_legacy_status_uses_reference_thresholds(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale(
            reference=(
                1000,
                1000,
                1000,
            )
        )

        self.assertEqual(
            grayscale.status(
                (
                    1200,
                    1000,
                    800,
                )
            ),
            [
                0,
                1,
                1,
            ],
        )

    def test_calibrated_status_uses_normalized_values(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        self.assertEqual(
            grayscale.status(
                raw=(
                    100,
                    500,
                    900,
                ),
                threshold=0.5,
            ),
            [
                0,
                0,
                1,
            ],
        )

    def test_status_rejects_boolean_threshold(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            TypeError,
            "threshold must be a number",
        ):
            grayscale.status(threshold=True)

    def test_status_rejects_non_finite_threshold(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        with self.assertRaisesRegex(
            ValueError,
            "threshold must be finite",
        ):
            grayscale.status(threshold=math.nan)

    def test_status_rejects_threshold_outside_range(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        for threshold in (
            -0.1,
            1.1,
        ):
            with (
                self.subTest(threshold=threshold),
                self.assertRaisesRegex(
                    GrayscaleError,
                    "threshold must be between 0.0 and 1.0",
                ),
            ):
                grayscale.status(threshold=threshold)

    def test_read_status_is_compatibility_alias(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()

        self.assertEqual(
            grayscale.read_status(
                datas=(
                    1200,
                    900,
                    800,
                ),
                threshold=0.25,
            ),
            grayscale.status(
                raw=(
                    1200,
                    900,
                    800,
                ),
                threshold=0.25,
            ),
        )

    def test_get_grayscale_normalized_is_compatibility_alias(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale(
            left_value=100,
            middle_value=500,
            right_value=900,
        )

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        self.assertEqual(
            grayscale.get_grayscale_normalized(),
            [
                0.0,
                0.5,
                1.0,
            ],
        )


class GrayscaleReadingTests(unittest.TestCase):
    def test_reading_without_calibration(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale(
            left_value=1200,
            middle_value=900,
            right_value=800,
            reference=(
                1000,
                1000,
                1000,
            ),
        )

        self.assertEqual(
            grayscale.reading(),
            GrayscaleReading(
                raw=(
                    1200,
                    900,
                    800,
                ),
                status=(
                    0,
                    1,
                    1,
                ),
                normalized=None,
            ),
        )

    def test_reading_with_calibration(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale(
            left_value=100,
            middle_value=500,
            right_value=900,
        )

        grayscale.set_calibration(
            floor=(
                100,
                100,
                100,
            ),
            line=(
                900,
                900,
                900,
            ),
        )

        self.assertEqual(
            grayscale.reading(threshold=0.5),
            GrayscaleReading(
                raw=(
                    100,
                    500,
                    900,
                ),
                status=(
                    0,
                    0,
                    1,
                ),
                normalized=(
                    0.0,
                    0.5,
                    1.0,
                ),
            ),
        )


class GrayscaleLifecycleTests(unittest.TestCase):
    def test_close_closes_channels_in_reverse_order(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale()

        close_order: list[str] = []

        original_left_close = left.close
        original_middle_close = middle.close
        original_right_close = right.close

        def close_left() -> None:
            close_order.append("left")
            original_left_close()

        def close_middle() -> None:
            close_order.append("middle")
            original_middle_close()

        def close_right() -> None:
            close_order.append("right")
            original_right_close()

        left.close = close_left
        middle.close = close_middle
        right.close = close_right

        grayscale.close()

        self.assertEqual(
            close_order,
            [
                "right",
                "middle",
                "left",
            ],
        )

        self.assertTrue(grayscale.closed)

    def test_close_is_idempotent(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale()

        grayscale.close()
        grayscale.close()

        self.assertEqual(
            left.close_count,
            1,
        )
        self.assertEqual(
            middle.close_count,
            1,
        )
        self.assertEqual(
            right.close_count,
            1,
        )

    def test_close_attempts_all_channels_and_raises_first_error(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale()

        right_error = HardwareError("right close failed")
        middle_error = HardwareError("middle close failed")

        right.close_error = right_error
        middle.close_error = middle_error

        with self.assertRaises(HardwareError) as raised:
            grayscale.close()

        self.assertIs(
            raised.exception,
            right_error,
        )

        self.assertEqual(
            left.close_count,
            1,
        )
        self.assertEqual(
            middle.close_count,
            1,
        )
        self.assertEqual(
            right.close_count,
            1,
        )
        self.assertTrue(grayscale.closed)

    def test_closed_sensor_rejects_operations(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()
        grayscale.close()

        operations = (
            lambda: grayscale.read(),
            lambda: grayscale.reference(),
            lambda: grayscale.set_calibration(
                (
                    100,
                    100,
                    100,
                ),
                (
                    900,
                    900,
                    900,
                ),
            ),
            lambda: grayscale.get_calibration(),
            lambda: grayscale.normalized(
                (
                    100,
                    200,
                    300,
                )
            ),
            lambda: grayscale.status(
                (
                    100,
                    200,
                    300,
                )
            ),
            lambda: grayscale.reading(),
        )

        for operation in operations:
            with (
                self.subTest(operation=operation),
                self.assertRaisesRegex(
                    GrayscaleError,
                    "grayscale sensor is closed",
                ),
            ):
                operation()

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale()

        with grayscale as entered:
            self.assertIs(
                entered,
                grayscale,
            )
            self.assertFalse(grayscale.closed)

        self.assertTrue(left.closed)
        self.assertTrue(middle.closed)
        self.assertTrue(right.closed)
        self.assertTrue(grayscale.closed)

    def test_closed_sensor_cannot_reenter_context(
        self,
    ) -> None:
        grayscale, _, _, _ = make_grayscale()
        grayscale.close()

        with (
            self.assertRaisesRegex(
                GrayscaleError,
                "grayscale sensor is closed",
            ),
            grayscale,
        ):
            pass

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        grayscale, left, middle, right = make_grayscale()

        grayscale.deinit()

        self.assertTrue(left.closed)
        self.assertTrue(middle.closed)
        self.assertTrue(right.closed)
        self.assertTrue(grayscale.closed)


if __name__ == "__main__":
    unittest.main()
