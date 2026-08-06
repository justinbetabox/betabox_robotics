from __future__ import annotations

import asyncio
import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

from betabox_robotics.calibration import CalibrationManager
from betabox_robotics.exceptions import BetaboxError
from betabox_robotics.launchpad.drive_controller import (
    ControlState,
    DriveControlError,
    ManualDriveController,
    _validate_axis,
    _validate_client_id,
    _validate_flag,
    _validate_generation,
    _validate_maximum_speed,
    _validate_number,
    _validate_positive_number,
    _validate_state,
)

MODULE = "betabox_robotics.launchpad.drive_controller"


def make_manager() -> CalibrationManager:
    return object.__new__(CalibrationManager)


def make_robot() -> Mock:
    robot = Mock()
    robot.config = SimpleNamespace(
        camera_mount=SimpleNamespace(
            pan_min_angle=-70.0,
            pan_center=5.0,
            pan_max_angle=80.0,
            tilt_min_angle=-30.0,
            tilt_center=10.0,
            tilt_max_angle=45.0,
        )
    )
    return robot


def make_controller(
    **kwargs: object,
) -> ManualDriveController:
    return ManualDriveController(
        make_manager(),
        **kwargs,
    )


class ValidationTests(unittest.TestCase):
    def test_validate_number_accepts_integer(self) -> None:
        self.assertEqual(
            _validate_number(
                3,
                name="value",
            ),
            3.0,
        )

    def test_validate_number_rejects_boolean(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "value must be a number",
        ):
            _validate_number(
                True,
                name="value",
            )

    def test_validate_number_rejects_non_finite(self) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be finite",
                ),
            ):
                _validate_number(
                    value,
                    name="value",
                )

    def test_validate_axis_accepts_limits(self) -> None:
        self.assertEqual(
            _validate_axis(
                -1,
                name="axis",
            ),
            -1.0,
        )
        self.assertEqual(
            _validate_axis(
                1,
                name="axis",
            ),
            1.0,
        )

    def test_validate_axis_rejects_out_of_range(self) -> None:
        for value in (
            -1.1,
            1.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "axis must be between -1.0 and 1.0",
                ),
            ):
                _validate_axis(
                    value,
                    name="axis",
                )

    def test_validate_flag(self) -> None:
        self.assertTrue(
            _validate_flag(
                True,
                name="flag",
            )
        )

        with self.assertRaisesRegex(
            TypeError,
            "flag must be a boolean",
        ):
            _validate_flag(
                1,
                name="flag",
            )

    def test_validate_positive_number(self) -> None:
        self.assertEqual(
            _validate_positive_number(
                2,
                name="value",
            ),
            2.0,
        )

        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "value must be greater than 0",
                ),
            ):
                _validate_positive_number(
                    value,
                    name="value",
                )

    def test_validate_generation(self) -> None:
        self.assertEqual(
            _validate_generation(0),
            0,
        )

        with self.assertRaisesRegex(
            TypeError,
            "generation must be an integer",
        ):
            _validate_generation(True)

        with self.assertRaisesRegex(
            ValueError,
            "generation cannot be negative",
        ):
            _validate_generation(-1)

    def test_validate_maximum_speed(self) -> None:
        for value in (
            1,
            100,
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    _validate_maximum_speed(value),
                    value,
                )

        with self.assertRaisesRegex(
            TypeError,
            "maximum_speed must be an integer",
        ):
            _validate_maximum_speed(50.5)

        for value in (
            0,
            101,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "maximum_speed must be between 1 and 100",
                ),
            ):
                _validate_maximum_speed(value)

    def test_validate_client_id_strips(self) -> None:
        self.assertEqual(
            _validate_client_id(" client "),
            "client",
        )

    def test_validate_client_id_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "client_id must be a string",
        ):
            _validate_client_id(1)

        with self.assertRaisesRegex(
            ValueError,
            "client_id cannot be empty",
        ):
            _validate_client_id(" ")

    def test_validate_state(self) -> None:
        state = ControlState()

        self.assertIs(
            _validate_state(state),
            state,
        )

        with self.assertRaisesRegex(
            TypeError,
            "state must be a ControlState",
        ):
            _validate_state(object())


class ControlStateTests(unittest.TestCase):
    def test_defaults(self) -> None:
        state = ControlState()

        self.assertEqual(state.throttle, 0.0)
        self.assertEqual(state.steering, 0.0)
        self.assertEqual(state.camera_pan, 0.0)
        self.assertEqual(state.camera_tilt, 0.0)
        self.assertFalse(state.headlights)
        self.assertFalse(state.horn)

    def test_normalizes_numeric_axes_to_float(self) -> None:
        state = ControlState(
            throttle=1,
            steering=-1,
            camera_pan=0,
            camera_tilt=1,
        )

        self.assertIsInstance(state.throttle, float)
        self.assertIsInstance(state.steering, float)
        self.assertEqual(state.throttle, 1.0)
        self.assertEqual(state.steering, -1.0)

    def test_rejects_invalid_axis(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "throttle must be between -1.0 and 1.0",
        ):
            ControlState(throttle=2.0)

    def test_rejects_invalid_flags(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "headlights must be a boolean",
        ):
            ControlState(
                headlights=1  # type: ignore[arg-type]
            )

        with self.assertRaisesRegex(
            TypeError,
            "horn must be a boolean",
        ):
            ControlState(
                horn=1  # type: ignore[arg-type]
            )

    def test_is_frozen_and_slotted(self) -> None:
        state = ControlState()

        self.assertFalse(
            hasattr(
                state,
                "__dict__",
            )
        )

        with self.assertRaises(FrozenInstanceError):
            state.throttle = 1.0  # type: ignore[misc]


class ConstructorTests(unittest.TestCase):
    def test_constructs_with_defaults(self) -> None:
        controller = make_controller()

        self.assertEqual(
            controller.heartbeat_timeout,
            1.0,
        )
        self.assertEqual(
            controller.update_hz,
            20.0,
        )
        self.assertEqual(
            controller.update_interval,
            0.05,
        )
        self.assertEqual(
            controller.maximum_speed,
            100,
        )
        self.assertEqual(
            controller.steering_angle,
            30.0,
        )
        self.assertTrue(controller.available)
        self.assertIsNone(controller.owner)

    def test_rejects_invalid_manager(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "calibration_manager must be a CalibrationManager",
        ):
            ManualDriveController(
                object()  # type: ignore[arg-type]
            )

    def test_rejects_invalid_timing_values(self) -> None:
        cases = (
            (
                {
                    "heartbeat_timeout": 0,
                },
                "heartbeat_timeout must be greater than 0",
            ),
            (
                {
                    "update_hz": 0,
                },
                "update_hz must be greater than 0",
            ),
            (
                {
                    "steering_angle": 0,
                },
                "steering_angle must be greater than 0",
            ),
        )

        for kwargs, message in cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaisesRegex(
                    ValueError,
                    message,
                ),
            ):
                make_controller(**kwargs)

    def test_rejects_noninteger_maximum_speed(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "maximum_speed must be an integer",
        ):
            make_controller(maximum_speed=50.5)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_creates_background_tasks(self) -> None:
        controller = make_controller()

        async def wait_forever() -> None:
            await asyncio.Future()

        with (
            patch.object(
                controller,
                "_watchdog_loop",
                side_effect=wait_forever,
            ),
            patch.object(
                controller,
                "_control_loop",
                side_effect=wait_forever,
            ),
        ):
            await controller.start()

            self.assertIsNotNone(controller._watchdog_task)
            self.assertIsNotNone(controller._control_task)
            self.assertEqual(
                controller._watchdog_task.get_name(),  # type: ignore[union-attr]
                "LaunchpadDriveWatchdog",
            )
            self.assertEqual(
                controller._control_task.get_name(),  # type: ignore[union-attr]
                "LaunchpadControlState",
            )

            await controller.close()

    async def test_start_is_idempotent_for_running_tasks(self) -> None:
        controller = make_controller()

        async def wait_forever() -> None:
            await asyncio.Future()

        with (
            patch.object(
                controller,
                "_watchdog_loop",
                side_effect=wait_forever,
            ),
            patch.object(
                controller,
                "_control_loop",
                side_effect=wait_forever,
            ),
        ):
            await controller.start()
            watchdog = controller._watchdog_task
            control = controller._control_task

            await controller.start()

            self.assertIs(
                controller._watchdog_task,
                watchdog,
            )
            self.assertIs(
                controller._control_task,
                control,
            )

            await controller.close()

    async def test_start_rejects_closed_controller(self) -> None:
        controller = make_controller()
        await controller.close()

        with self.assertRaisesRegex(
            DriveControlError,
            "manual drive controller is closed",
        ):
            await controller.start()

    async def test_close_resets_state_and_closes_robot(self) -> None:
        controller = make_controller()
        robot = make_robot()

        controller._owner = "client"
        controller._claiming = "claiming"
        controller._robot = robot
        controller._desired_state = ControlState(
            throttle=1.0,
        )
        controller._last_applied_state = ControlState(
            throttle=1.0,
        )
        previous_generation = controller._state_generation

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(return_value=None),
        ) as to_thread:
            await controller.close()

        self.assertTrue(controller._closed)
        self.assertIsNone(controller._owner)
        self.assertIsNone(controller._claiming)
        self.assertIsNone(controller._robot)
        self.assertEqual(
            controller._desired_state,
            ControlState(),
        )
        self.assertIsNone(controller._last_applied_state)
        self.assertEqual(
            controller._state_generation,
            previous_generation + 1,
        )
        to_thread.assert_awaited_once_with(robot.close)

    async def test_close_is_idempotent(self) -> None:
        controller = make_controller()

        with patch.object(
            controller,
            "_stop_center_close",
            new=AsyncMock(),
        ) as stop_close:
            await controller.close()
            await controller.close()

        stop_close.assert_awaited_once_with(None)

    async def test_close_suppresses_cleanup_failure(self) -> None:
        controller = make_controller()
        controller._robot = make_robot()

        with patch.object(
            controller,
            "_stop_center_close",
            new=AsyncMock(side_effect=DriveControlError("close failed")),
        ):
            await controller.close()

        self.assertTrue(controller._closed)


class OwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_owns_requires_open_owner_and_robot(self) -> None:
        controller = make_controller()
        controller._owner = "client"
        controller._robot = make_robot()

        self.assertTrue(await controller.owns(" client "))
        self.assertFalse(await controller.owns("other"))

        controller._robot = None

        self.assertFalse(await controller.owns("client"))

    async def test_claim_success(self) -> None:
        controller = make_controller()
        robot = make_robot()

        with (
            patch.object(
                controller,
                "_ensure_robot",
                new=AsyncMock(),
            ) as ensure,
            patch.object(
                controller,
                "_safe_neutralize",
                new=AsyncMock(),
            ) as neutralize,
            patch(
                f"{MODULE}.time.monotonic",
                return_value=25.0,
            ),
        ):
            controller._robot = robot
            result = await controller.claim(" client ")

        self.assertTrue(result)
        self.assertEqual(
            controller.owner,
            "client",
        )
        self.assertIsNone(controller._claiming)
        self.assertEqual(
            controller._last_heartbeat,
            25.0,
        )
        ensure.assert_awaited_once_with()
        neutralize.assert_awaited_once_with()

    async def test_claim_rejects_existing_owner(self) -> None:
        controller = make_controller()
        controller._owner = "first"

        with patch.object(
            controller,
            "_ensure_robot",
            new=AsyncMock(),
        ) as ensure:
            result = await controller.claim("second")

        self.assertFalse(result)
        ensure.assert_not_awaited()

    async def test_claim_rejects_concurrent_claim(self) -> None:
        controller = make_controller()
        controller._claiming = "first"

        self.assertFalse(await controller.claim("second"))

    async def test_failed_claim_resets_and_closes_robot(self) -> None:
        controller = make_controller()
        robot = make_robot()
        controller._robot = robot

        with (
            patch.object(
                controller,
                "_ensure_robot",
                new=AsyncMock(),
            ),
            patch.object(
                controller,
                "_safe_neutralize",
                new=AsyncMock(side_effect=DriveControlError("stop failed")),
            ),
            patch.object(
                controller,
                "_stop_center_close",
                new=AsyncMock(),
            ) as close_robot,
            self.assertRaisesRegex(
                DriveControlError,
                "stop failed",
            ),
        ):
            await controller.claim("client")

        self.assertIsNone(controller.owner)
        self.assertIsNone(controller._claiming)
        self.assertIsNone(controller._robot)
        close_robot.assert_awaited_once_with(robot)

    async def test_release_owner_resets_and_closes(self) -> None:
        controller = make_controller()
        robot = make_robot()
        controller._owner = "client"
        controller._robot = robot
        controller._desired_state = ControlState(
            throttle=1.0,
        )

        with patch.object(
            controller,
            "_stop_center_close",
            new=AsyncMock(),
        ) as close_robot:
            await controller.release(" client ")

        self.assertIsNone(controller.owner)
        self.assertIsNone(controller._robot)
        self.assertEqual(
            controller._desired_state,
            ControlState(),
        )
        close_robot.assert_awaited_once_with(robot)

    async def test_release_non_owner_does_nothing(self) -> None:
        controller = make_controller()
        controller._owner = "client"
        controller._robot = make_robot()

        with patch.object(
            controller,
            "_stop_center_close",
            new=AsyncMock(),
        ) as close_robot:
            await controller.release("other")

        self.assertEqual(
            controller.owner,
            "client",
        )
        close_robot.assert_not_awaited()

    async def test_heartbeat_updates_timestamp_for_owner(self) -> None:
        controller = make_controller()
        controller._owner = "client"

        with patch(
            f"{MODULE}.time.monotonic",
            return_value=50.0,
        ):
            await controller.heartbeat("client")

        self.assertEqual(
            controller._last_heartbeat,
            50.0,
        )

    async def test_heartbeat_rejects_non_owner(self) -> None:
        controller = make_controller()

        with self.assertRaisesRegex(
            DriveControlError,
            "manual drive control is not owned by this client",
        ):
            await controller.heartbeat("client")

    async def test_update_state_updates_generation_and_heartbeat(self) -> None:
        controller = make_controller()
        controller._owner = "client"
        state = ControlState(
            throttle=0.5,
        )
        generation = controller._state_generation

        with patch(
            f"{MODULE}.time.monotonic",
            return_value=70.0,
        ):
            await controller.update_state(
                "client",
                state,
            )

        self.assertIs(
            controller._desired_state,
            state,
        )
        self.assertEqual(
            controller._state_generation,
            generation + 1,
        )
        self.assertEqual(
            controller._last_heartbeat,
            70.0,
        )

    async def test_update_state_rejects_invalid_state(self) -> None:
        controller = make_controller()

        with self.assertRaisesRegex(
            TypeError,
            "state must be a ControlState",
        ):
            await controller.update_state(
                "client",
                object(),  # type: ignore[arg-type]
            )

    async def test_emergency_stop_preserves_camera_and_headlights(self) -> None:
        controller = make_controller()
        controller._owner = "client"
        controller._desired_state = ControlState(
            throttle=1.0,
            steering=1.0,
            camera_pan=0.5,
            camera_tilt=-0.5,
            headlights=True,
            horn=True,
        )

        with patch.object(
            controller,
            "_safe_neutralize",
            new=AsyncMock(),
        ) as neutralize:
            await controller.emergency_stop("client")

        self.assertEqual(
            controller._desired_state,
            ControlState(
                camera_pan=0.5,
                camera_tilt=-0.5,
                headlights=True,
                horn=False,
            ),
        )
        neutralize.assert_awaited_once_with()

    async def test_emergency_stop_non_owner_does_nothing(self) -> None:
        controller = make_controller()
        controller._owner = "client"

        with patch.object(
            controller,
            "_safe_neutralize",
            new=AsyncMock(),
        ) as neutralize:
            await controller.emergency_stop("other")

        neutralize.assert_not_awaited()


class RobotManagementTests(unittest.IsolatedAsyncioTestCase):
    async def test_ensure_robot_uses_calibration_manager(self) -> None:
        manager = make_manager()
        controller = ManualDriveController(manager)
        robot = make_robot()

        with (
            patch.object(
                manager,
                "create_car",
                return_value=robot,
                create=True,
            ) as create_car,
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(return_value=robot),
            ) as to_thread,
        ):
            await controller._ensure_robot()

        to_thread.assert_awaited_once_with(
            create_car,
            owner="Manual Drive",
        )
        self.assertIs(
            controller._robot,
            robot,
        )

    async def test_ensure_robot_does_not_recreate_existing_robot(self) -> None:
        controller = make_controller()
        controller._robot = make_robot()

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(),
        ) as to_thread:
            await controller._ensure_robot()

        to_thread.assert_not_awaited()

    async def test_ensure_robot_rejects_none(
        self,
    ) -> None:
        controller = make_controller()

        with (
            patch.object(
                controller.calibration_manager,
                "create_car",
                create=True,
            ) as create_car,
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(
                    return_value=None,
                ),
            ) as to_thread,
            self.assertRaisesRegex(
                DriveControlError,
                "failed to create robot",
            ),
        ):
            await controller._ensure_robot()

        to_thread.assert_awaited_once_with(
            create_car,
            owner="Manual Drive",
        )

    async def test_stop_center_close_closes_robot(self) -> None:
        controller = make_controller()
        robot = make_robot()

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(),
        ) as to_thread:
            await controller._stop_center_close(robot)

        to_thread.assert_awaited_once_with(robot.close)

    async def test_stop_center_close_wraps_error(self) -> None:
        controller = make_controller()
        robot = make_robot()

        with (
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(side_effect=RuntimeError("close failed")),
            ),
            self.assertRaisesRegex(
                DriveControlError,
                "failed to close robot: close failed",
            ),
        ):
            await controller._stop_center_close(robot)

    async def test_safe_neutralize_stops_and_centers(self) -> None:
        controller = make_controller()
        robot = make_robot()
        controller._robot = robot

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(),
        ) as to_thread:
            await controller._safe_neutralize()

        self.assertEqual(
            to_thread.await_args_list,
            [
                call(robot.stop),
                call(robot.center),
            ],
        )

    async def test_safe_neutralize_wraps_stop_error(self) -> None:
        controller = make_controller()
        robot = make_robot()
        controller._robot = robot

        async def to_thread_side_effect(
            function: object,
            *args: object,
            **kwargs: object,
        ) -> object:
            if function == robot.stop:
                raise BetaboxError("stop failed")
            return None

        with (
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(side_effect=to_thread_side_effect),
            ),
            self.assertRaisesRegex(
                DriveControlError,
                "failed to stop robot: stop failed",
            ),
        ):
            await controller._safe_neutralize()

    async def test_safe_neutralize_ignores_center_error(self) -> None:
        controller = make_controller()
        robot = make_robot()
        controller._robot = robot

        async def to_thread_side_effect(
            function: object,
            *args: object,
            **kwargs: object,
        ) -> object:
            if function == robot.center:
                raise BetaboxError("center failed")
            return None

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(side_effect=to_thread_side_effect),
        ):
            await controller._safe_neutralize()


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_throttle_forward(self) -> None:
        controller = make_controller(maximum_speed=80)
        robot = make_robot()
        controller._robot = robot

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(),
        ) as to_thread:
            await controller._apply_throttle(0.5)

        to_thread.assert_awaited_once_with(
            robot.forward,
            40,
        )

    async def test_apply_throttle_backward(self) -> None:
        controller = make_controller(maximum_speed=80)
        robot = make_robot()
        controller._robot = robot

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(),
        ) as to_thread:
            await controller._apply_throttle(-0.5)

        to_thread.assert_awaited_once_with(
            robot.backward,
            40,
        )

    async def test_apply_throttle_zero_stops(self) -> None:
        controller = make_controller()
        controller._robot = make_robot()

        with patch.object(
            controller,
            "_stop_motion",
            new=AsyncMock(),
        ) as stop:
            await controller._apply_throttle(0.0)

        stop.assert_awaited_once_with()

    async def test_apply_throttle_wraps_hardware_error(self) -> None:
        controller = make_controller()
        controller._robot = make_robot()

        with (
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(side_effect=RuntimeError("motor failed")),
            ),
            self.assertRaisesRegex(
                DriveControlError,
                "failed to apply throttle: motor failed",
            ),
        ):
            await controller._apply_throttle(1.0)

    async def test_apply_steering_left_right_and_center(self) -> None:
        controller = make_controller(steering_angle=30.0)
        robot = make_robot()
        controller._robot = robot

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(),
        ) as to_thread:
            await controller._apply_steering_axis(-0.5)
            await controller._apply_steering_axis(0.5)
            await controller._apply_steering_axis(0.0)

        self.assertEqual(
            to_thread.await_args_list,
            [
                call(
                    robot.left,
                    15.0,
                ),
                call(
                    robot.right,
                    15.0,
                ),
                call(robot.center),
            ],
        )

    async def test_apply_camera_axes_maps_angles(self) -> None:
        controller = make_controller()
        robot = make_robot()
        controller._robot = robot

        with patch(
            f"{MODULE}.asyncio.to_thread",
            new=AsyncMock(),
        ) as to_thread:
            await controller._apply_camera_axes(
                -1.0,
                1.0,
            )

        to_thread.assert_awaited_once_with(
            robot.look,
            pan=-70.0,
            tilt=45.0,
            smooth=False,
        )

    def test_camera_axis_to_angle(self) -> None:
        controller = make_controller()

        self.assertEqual(
            controller._camera_axis_to_angle(
                -1.0,
                minimum=-70.0,
                center=5.0,
                maximum=80.0,
            ),
            -70.0,
        )
        self.assertEqual(
            controller._camera_axis_to_angle(
                0.0,
                minimum=-70.0,
                center=5.0,
                maximum=80.0,
            ),
            5.0,
        )
        self.assertEqual(
            controller._camera_axis_to_angle(
                1.0,
                minimum=-70.0,
                center=5.0,
                maximum=80.0,
            ),
            80.0,
        )

    def test_camera_axis_to_angle_rejects_invalid_range(self) -> None:
        controller = make_controller()

        with self.assertRaisesRegex(
            ValueError,
            "camera angles must satisfy minimum <= center <= maximum",
        ):
            controller._camera_axis_to_angle(
                0.0,
                minimum=10.0,
                center=0.0,
                maximum=20.0,
            )

    async def test_apply_state_skips_stale_generation(self) -> None:
        controller = make_controller()
        controller._owner = "client"
        controller._robot = make_robot()
        controller._state_generation = 2

        with patch.object(
            controller,
            "_apply_steering_axis",
            new=AsyncMock(),
        ) as steering:
            await controller._apply_state(
                ControlState(steering=1.0),
                1,
            )

        steering.assert_not_awaited()

    async def test_apply_state_only_applies_changed_values(self) -> None:
        controller = make_controller()
        controller._owner = "client"
        controller._robot = make_robot()
        controller._state_generation = 1
        previous = ControlState(
            throttle=0.5,
            steering=0.0,
            camera_pan=0.0,
            camera_tilt=0.0,
        )
        current = ControlState(
            throttle=0.5,
            steering=1.0,
            camera_pan=0.0,
            camera_tilt=0.0,
        )
        controller._last_applied_state = previous

        with (
            patch.object(
                controller,
                "_apply_steering_axis",
                new=AsyncMock(),
            ) as steering,
            patch.object(
                controller,
                "_apply_throttle",
                new=AsyncMock(),
            ) as throttle,
            patch.object(
                controller,
                "_apply_camera_axes",
                new=AsyncMock(),
            ) as camera,
        ):
            await controller._apply_state(
                current,
                1,
            )

        steering.assert_awaited_once_with(1.0)
        throttle.assert_not_awaited()
        camera.assert_not_awaited()
        self.assertIs(
            controller._last_applied_state,
            current,
        )


class WatchdogTests(unittest.IsolatedAsyncioTestCase):
    async def test_watchdog_releases_expired_owner(self) -> None:
        controller = make_controller(heartbeat_timeout=1.0)
        robot = make_robot()
        controller._owner = "client"
        controller._robot = robot
        controller._last_heartbeat = 1.0

        async def sleep_side_effect(
            delay: float,
        ) -> None:
            if controller._owner is None:
                raise asyncio.CancelledError()

        with (
            patch(
                f"{MODULE}.time.monotonic",
                return_value=3.0,
            ),
            patch(
                f"{MODULE}.asyncio.sleep",
                new=AsyncMock(side_effect=sleep_side_effect),
            ),
            patch.object(
                controller,
                "_stop_center_close",
                new=AsyncMock(),
            ) as close_robot,
            self.assertRaises(asyncio.CancelledError),
        ):
            await controller._watchdog_loop()

        self.assertIsNone(controller._owner)
        self.assertIsNone(controller._robot)
        close_robot.assert_awaited_once_with(robot)

    async def test_watchdog_keeps_fresh_owner(self) -> None:
        controller = make_controller(heartbeat_timeout=5.0)
        controller._owner = "client"
        controller._robot = make_robot()
        controller._last_heartbeat = 9.0
        calls = 0

        async def sleep_side_effect(
            delay: float,
        ) -> None:
            nonlocal calls
            calls += 1

            if calls > 1:
                raise asyncio.CancelledError()

        with (
            patch(
                f"{MODULE}.time.monotonic",
                return_value=10.0,
            ),
            patch(
                f"{MODULE}.asyncio.sleep",
                new=AsyncMock(side_effect=sleep_side_effect),
            ),
            patch.object(
                controller,
                "_stop_center_close",
                new=AsyncMock(),
            ) as close_robot,
            self.assertRaises(asyncio.CancelledError),
        ):
            await controller._watchdog_loop()

        self.assertEqual(
            controller._owner,
            "client",
        )
        close_robot.assert_not_awaited()


class RequirementTests(unittest.TestCase):
    def test_require_open(self) -> None:
        controller = make_controller()
        controller._require_open()

        controller._closed = True

        with self.assertRaisesRegex(
            DriveControlError,
            "manual drive controller is closed",
        ):
            controller._require_open()

    def test_require_owner(self) -> None:
        controller = make_controller()
        controller._owner = "client"

        controller._require_owner(" client ")

        with self.assertRaisesRegex(
            DriveControlError,
            "manual drive control is not owned by this client",
        ):
            controller._require_owner("other")

    def test_require_robot(self) -> None:
        controller = make_controller()
        robot = make_robot()
        controller._robot = robot

        self.assertIs(
            controller._require_robot(),
            robot,
        )

        controller._robot = None

        with self.assertRaisesRegex(
            DriveControlError,
            "robot is not started",
        ):
            controller._require_robot()


if __name__ == "__main__":
    unittest.main()
