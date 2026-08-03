from __future__ import annotations

import math
import unittest
from unittest.mock import patch

from betabox_robotics.camera import (
    CameraMount,
    CameraMountError,
    CameraMountStatus,
)
from betabox_robotics.hardware import (
    HardwareError,
    Pins,
)
from betabox_robotics.robots.config import (
    CameraMountConfig,
)


class FakeServo:
    instances: list[FakeServo] = []
    construction_error_at: int | None = None

    def __init__(
        self,
        channel,
        *,
        min_angle: float = -90,
        max_angle: float = 90,
        offset: float = 0,
        **kwargs,
    ) -> None:
        instance_number = len(FakeServo.instances)

        if FakeServo.construction_error_at == instance_number:
            raise HardwareError("servo construction failed")

        self.channel = channel
        self.min_angle = float(min_angle)
        self.max_angle = float(max_angle)
        self.offset = float(offset)

        self.moves: list[
            tuple[
                float,
                bool,
            ]
        ] = []

        self._angle: float | None = None
        self.closed = False

        self.move_error: Exception | None = None
        self.close_error: Exception | None = None
        self.report_position = True

        FakeServo.instances.append(self)

    def move_to(
        self,
        angle: float,
        *,
        smooth: bool = True,
    ) -> None:
        if self.move_error is not None:
            raise self.move_error

        requested = float(angle)

        physical = max(
            self.min_angle,
            min(
                self.max_angle,
                requested + self.offset,
            ),
        )

        effective_logical = physical - self.offset

        self.moves.append(
            (
                requested,
                smooth,
            )
        )

        if self.report_position:
            self._angle = effective_logical
        else:
            self._angle = None

    def get_angle(
        self,
    ) -> float | None:
        return self._angle

    def close(self) -> None:
        self.closed = True

        if self.close_error is not None:
            raise self.close_error


def make_config(
    *,
    pan_min: float = -45.0,
    pan_max: float = 45.0,
    tilt_min: float = -30.0,
    tilt_max: float = 45.0,
    pan_center: float = 0.0,
    tilt_center: float = 5.0,
    pan_reversed: bool = False,
    tilt_reversed: bool = False,
) -> CameraMountConfig:
    return CameraMountConfig(
        pan_servo=Pins.P0,
        tilt_servo=Pins.P1,
        pan_min_angle=pan_min,
        pan_max_angle=pan_max,
        tilt_min_angle=tilt_min,
        tilt_max_angle=tilt_max,
        pan_center=pan_center,
        tilt_center=tilt_center,
        pan_reversed=pan_reversed,
        tilt_reversed=tilt_reversed,
    )


def make_mount(
    *,
    config: CameraMountConfig | None = None,
    pan_offset: float = 0.0,
    tilt_offset: float = 0.0,
) -> tuple[
    CameraMount,
    FakeServo,
    FakeServo,
]:
    FakeServo.instances.clear()
    FakeServo.construction_error_at = None

    mount = CameraMount(
        config or make_config(),
        pan_offset=pan_offset,
        tilt_offset=tilt_offset,
    )

    if len(FakeServo.instances) != 2:
        raise AssertionError("expected two fake servos")

    return (
        mount,
        FakeServo.instances[0],
        FakeServo.instances[1],
    )


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
class CameraMountConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeServo.instances.clear()
        FakeServo.construction_error_at = None

    def tearDown(self) -> None:
        FakeServo.instances.clear()
        FakeServo.construction_error_at = None

    def test_constructs_configured_servos(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount(
            pan_offset=2.5,
            tilt_offset=-3.0,
        )

        self.assertEqual(
            pan_servo.channel,
            Pins.P0,
        )
        self.assertEqual(
            tilt_servo.channel,
            Pins.P1,
        )

        self.assertEqual(
            pan_servo.min_angle,
            -45.0,
        )
        self.assertEqual(
            pan_servo.max_angle,
            45.0,
        )
        self.assertEqual(
            pan_servo.offset,
            2.5,
        )

        self.assertEqual(
            tilt_servo.min_angle,
            -30.0,
        )
        self.assertEqual(
            tilt_servo.max_angle,
            45.0,
        )
        self.assertEqual(
            tilt_servo.offset,
            -3.0,
        )

        self.assertFalse(mount.closed)

    def test_initial_position_is_unknown(
        self,
    ) -> None:
        mount, _, _ = make_mount()

        self.assertIsNone(mount.pan_angle)
        self.assertIsNone(mount.tilt_angle)

        status = mount.status()

        self.assertIsNone(status.pan)
        self.assertIsNone(status.tilt)

    def test_default_delegates_to_constructor(
        self,
    ) -> None:
        config = make_config()

        mount = CameraMount.default(
            config,
            pan_offset=3,
            tilt_offset=-2,
        )

        self.assertEqual(
            mount.pan_offset,
            3.0,
        )
        self.assertEqual(
            mount.tilt_offset,
            -2.0,
        )

    def test_reversed_pan_transforms_asymmetric_limits(
        self,
    ) -> None:
        config = make_config(
            pan_min=-20,
            pan_max=40,
            pan_reversed=True,
        )

        _, pan_servo, _ = make_mount(config=config)

        self.assertEqual(
            pan_servo.min_angle,
            -40.0,
        )
        self.assertEqual(
            pan_servo.max_angle,
            20.0,
        )

    def test_reversed_tilt_transforms_asymmetric_limits(
        self,
    ) -> None:
        config = make_config(
            tilt_min=-10,
            tilt_max=35,
            tilt_reversed=True,
        )

        _, _, tilt_servo = make_mount(config=config)

        self.assertEqual(
            tilt_servo.min_angle,
            -35.0,
        )
        self.assertEqual(
            tilt_servo.max_angle,
            10.0,
        )

    def test_rejects_boolean_offset(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "pan_offset must be a number",
        ):
            CameraMount(
                make_config(),
                pan_offset=True,
            )

    def test_rejects_non_finite_offset(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "tilt_offset must be finite",
        ):
            CameraMount(
                make_config(),
                tilt_offset=math.inf,
            )

    def test_closes_pan_servo_when_tilt_construction_fails(
        self,
    ) -> None:
        FakeServo.construction_error_at = 1

        with self.assertRaisesRegex(
            HardwareError,
            "servo construction failed",
        ):
            CameraMount(make_config())

        self.assertEqual(
            len(FakeServo.instances),
            1,
        )
        self.assertTrue(FakeServo.instances[0].closed)


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
class CameraMountMovementTests(unittest.TestCase):
    def test_look_moves_both_axes(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.look(
            pan=20,
            tilt=-10,
            smooth=False,
        )

        self.assertEqual(
            pan_servo.moves[-1],
            (
                20.0,
                False,
            ),
        )

        self.assertEqual(
            tilt_servo.moves[-1],
            (
                -10.0,
                False,
            ),
        )

        self.assertEqual(
            mount.pan_angle,
            20.0,
        )
        self.assertEqual(
            mount.tilt_angle,
            -10.0,
        )

    def test_look_validates_both_axes_before_moving(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        with self.assertRaisesRegex(
            TypeError,
            "tilt must be a number",
        ):
            mount.look(
                pan=20,
                tilt=True,
            )

        self.assertEqual(
            pan_servo.moves,
            [],
        )
        self.assertEqual(
            tilt_servo.moves,
            [],
        )

    def test_look_with_no_axes_does_nothing(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.look()

        self.assertEqual(
            pan_servo.moves,
            [],
        )
        self.assertEqual(
            tilt_servo.moves,
            [],
        )

    def test_pan_preserves_tilt_state(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.tilt(15)
        tilt_move_count = len(tilt_servo.moves)

        mount.pan(25)

        self.assertEqual(
            mount.pan_angle,
            25.0,
        )
        self.assertEqual(
            mount.tilt_angle,
            15.0,
        )

        self.assertEqual(
            len(tilt_servo.moves),
            tilt_move_count,
        )
        self.assertEqual(
            len(pan_servo.moves),
            1,
        )

    def test_tilt_preserves_pan_state(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.pan(-20)
        pan_move_count = len(pan_servo.moves)

        mount.tilt(25)

        self.assertEqual(
            mount.pan_angle,
            -20.0,
        )
        self.assertEqual(
            mount.tilt_angle,
            25.0,
        )

        self.assertEqual(
            len(pan_servo.moves),
            pan_move_count,
        )
        self.assertEqual(
            len(tilt_servo.moves),
            1,
        )

    def test_clamps_logical_angles(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.pan(100)
        mount.tilt(-100)

        self.assertEqual(
            pan_servo.moves[-1][0],
            45.0,
        )
        self.assertEqual(
            tilt_servo.moves[-1][0],
            -30.0,
        )

        self.assertEqual(
            mount.pan_angle,
            45.0,
        )
        self.assertEqual(
            mount.tilt_angle,
            -30.0,
        )

    def test_pan_reversed_inverts_servo_angle(
        self,
    ) -> None:
        mount, pan_servo, _ = make_mount(
            config=make_config(
                pan_reversed=True,
            )
        )

        mount.pan(30)

        self.assertEqual(
            pan_servo.moves[-1][0],
            -30.0,
        )
        self.assertEqual(
            mount.pan_angle,
            30.0,
        )

    def test_tilt_reversed_inverts_servo_angle(
        self,
    ) -> None:
        mount, _, tilt_servo = make_mount(
            config=make_config(
                tilt_reversed=True,
            )
        )

        mount.tilt(20)

        self.assertEqual(
            tilt_servo.moves[-1][0],
            -20.0,
        )
        self.assertEqual(
            mount.tilt_angle,
            20.0,
        )

    def test_center_uses_configured_values(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.center(smooth=False)

        self.assertEqual(
            pan_servo.moves[-1],
            (
                0.0,
                False,
            ),
        )
        self.assertEqual(
            tilt_servo.moves[-1],
            (
                5.0,
                False,
            ),
        )

        self.assertEqual(
            mount.pan_angle,
            0.0,
        )
        self.assertEqual(
            mount.tilt_angle,
            5.0,
        )

    def test_pan_offset_reports_effective_logical_angle(
        self,
    ) -> None:
        mount, _, _ = make_mount(
            pan_offset=5,
        )

        mount.pan(10)

        self.assertEqual(
            mount.pan_angle,
            10.0,
        )
        self.assertEqual(
            mount.pan_offset,
            5.0,
        )

    def test_pan_rejects_boolean_angle(
        self,
    ) -> None:
        mount, _, _ = make_mount()

        with self.assertRaisesRegex(
            TypeError,
            "pan must be a number",
        ):
            mount.pan(True)

    def test_tilt_rejects_non_finite_angle(
        self,
    ) -> None:
        mount, _, _ = make_mount()

        with self.assertRaisesRegex(
            ValueError,
            "tilt must be finite",
        ):
            mount.tilt(math.nan)

    def test_rejects_invalid_smooth_type(
        self,
    ) -> None:
        mount, _, _ = make_mount()

        with self.assertRaisesRegex(
            TypeError,
            "smooth must be a boolean",
        ):
            mount.look(
                pan=10,
                smooth=1,  # type: ignore[arg-type]
            )

    def test_wraps_pan_hardware_error(
        self,
    ) -> None:
        mount, pan_servo, _ = make_mount()

        pan_servo.move_error = HardwareError("pan motor failure")

        with self.assertRaisesRegex(
            CameraMountError,
            "camera pan failed",
        ) as raised:
            mount.pan(20)

        self.assertIsInstance(
            raised.exception.__cause__,
            HardwareError,
        )
        self.assertIsNone(
            mount.pan_angle,
        )

    def test_wraps_tilt_hardware_error(
        self,
    ) -> None:
        mount, _, tilt_servo = make_mount()

        tilt_servo.move_error = HardwareError("tilt motor failure")

        with self.assertRaisesRegex(
            CameraMountError,
            "camera tilt failed",
        ):
            mount.tilt(20)

        self.assertIsNone(
            mount.tilt_angle,
        )

    def test_rejects_missing_pan_position_report(
        self,
    ) -> None:
        mount, pan_servo, _ = make_mount()
        pan_servo.report_position = False

        with self.assertRaisesRegex(
            CameraMountError,
            "pan servo did not report",
        ):
            mount.pan(10)

    def test_rejects_missing_tilt_position_report(
        self,
    ) -> None:
        mount, _, tilt_servo = make_mount()
        tilt_servo.report_position = False

        with self.assertRaisesRegex(
            CameraMountError,
            "tilt servo did not report",
        ):
            mount.tilt(10)


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
class CameraMountStatusTests(unittest.TestCase):
    def test_status_reports_configuration_and_position(
        self,
    ) -> None:
        mount, _, _ = make_mount(
            pan_offset=2,
            tilt_offset=-3,
        )

        mount.look(
            pan=15,
            tilt=-10,
        )

        self.assertEqual(
            mount.status(),
            CameraMountStatus(
                pan=15.0,
                tilt=-10.0,
                pan_offset=2.0,
                tilt_offset=-3.0,
                pan_min=-45.0,
                pan_max=45.0,
                tilt_min=-30.0,
                tilt_max=45.0,
            ),
        )

    def test_status_to_dict(
        self,
    ) -> None:
        status = CameraMountStatus(
            pan=None,
            tilt=None,
            pan_offset=1.0,
            tilt_offset=2.0,
            pan_min=-45.0,
            pan_max=45.0,
            tilt_min=-30.0,
            tilt_max=45.0,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "pan": None,
                "tilt": None,
                "pan_offset": 1.0,
                "tilt_offset": 2.0,
                "pan_min": -45.0,
                "pan_max": 45.0,
                "tilt_min": -30.0,
                "tilt_max": 45.0,
            },
        )


@patch(
    "betabox_robotics.camera.mount.Servo",
    FakeServo,
)
class CameraMountLifecycleTests(unittest.TestCase):
    def test_close_closes_both_servos(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.close()

        self.assertTrue(mount.closed)
        self.assertTrue(pan_servo.closed)
        self.assertTrue(tilt_servo.closed)
        self.assertIsNone(mount.pan_angle)
        self.assertIsNone(mount.tilt_angle)

    def test_close_is_idempotent(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.close()
        mount.close()

        self.assertTrue(pan_servo.closed)
        self.assertTrue(tilt_servo.closed)

    def test_close_attempts_both_and_raises_first_error(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        tilt_error = HardwareError("tilt close failed")
        pan_error = HardwareError("pan close failed")

        tilt_servo.close_error = tilt_error
        pan_servo.close_error = pan_error

        with self.assertRaises(HardwareError) as raised:
            mount.close()

        self.assertIs(
            raised.exception,
            tilt_error,
        )
        self.assertTrue(tilt_servo.closed)
        self.assertTrue(pan_servo.closed)
        self.assertTrue(mount.closed)

    def test_closed_mount_rejects_operations(
        self,
    ) -> None:
        mount, _, _ = make_mount()
        mount.close()

        operations = (
            lambda: mount.look(pan=10),
            lambda: mount.pan(10),
            lambda: mount.tilt(10),
            lambda: mount.center(),
            lambda: mount.status(),
        )

        for operation in operations:
            with (
                self.subTest(
                    operation=operation,
                ),
                self.assertRaisesRegex(
                    CameraMountError,
                    "camera mount is closed",
                ),
            ):
                operation()

    def test_context_manager_returns_self_and_closes(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        with mount as entered:
            self.assertIs(
                entered,
                mount,
            )
            self.assertFalse(mount.closed)

        self.assertTrue(pan_servo.closed)
        self.assertTrue(tilt_servo.closed)
        self.assertTrue(mount.closed)

    def test_closed_mount_cannot_reenter_context(
        self,
    ) -> None:
        mount, _, _ = make_mount()
        mount.close()

        with (
            self.assertRaisesRegex(
                CameraMountError,
                "camera mount is closed",
            ),
            mount,
        ):
            pass

    def test_deinit_delegates_to_close(
        self,
    ) -> None:
        mount, pan_servo, tilt_servo = make_mount()

        mount.deinit()

        self.assertTrue(pan_servo.closed)
        self.assertTrue(tilt_servo.closed)
        self.assertTrue(mount.closed)


if __name__ == "__main__":
    unittest.main()
