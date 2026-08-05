from __future__ import annotations

import unittest

from betabox_robotics.robots.base import RobotBase
from betabox_robotics.robots.capabilities import (
    RobotCapability,
)
from betabox_robotics.robots.exceptions import (
    RobotLifecycleError,
)


class DriveRobot(RobotBase):
    capabilities = frozenset(
        {
            RobotCapability.DRIVE,
            RobotCapability.SYSTEM,
        }
    )


class TrackingRobot(RobotBase):
    def __init__(self) -> None:
        super().__init__()
        self.stop_calls = 0

    def stop_all(self) -> None:
        self.stop_calls += 1
        super().stop_all()


class RobotBaseConstructionTests(unittest.TestCase):
    def test_initial_state(self) -> None:
        robot = RobotBase()

        self.assertFalse(robot.started)
        self.assertFalse(robot.closed)

    def test_default_capabilities_are_empty(
        self,
    ) -> None:
        robot = RobotBase()

        self.assertEqual(
            robot.capabilities,
            frozenset(),
        )
        self.assertEqual(
            robot.capability_names(),
            (),
        )

    def test_capabilities_are_immutable(
        self,
    ) -> None:
        robot = DriveRobot()

        with self.assertRaises(AttributeError):
            robot.capabilities.add(  # type: ignore[attr-defined]
                RobotCapability.AUDIO
            )


class RobotBaseGuardTests(unittest.TestCase):
    def test_require_open_while_open(
        self,
    ) -> None:
        robot = RobotBase()

        self.assertIsNone(robot.require_open())

    def test_require_open_rejects_closed_robot(
        self,
    ) -> None:
        robot = RobotBase()
        robot.close()

        with self.assertRaisesRegex(
            RobotLifecycleError,
            "robot is closed",
        ):
            robot.require_open()

    def test_require_started_when_started(
        self,
    ) -> None:
        robot = RobotBase()
        robot.start()

        self.assertIsNone(robot.require_started())

    def test_require_started_before_start(
        self,
    ) -> None:
        robot = RobotBase()

        with self.assertRaisesRegex(
            RobotLifecycleError,
            "robot is not started",
        ):
            robot.require_started()

    def test_require_started_after_close_reports_closed(
        self,
    ) -> None:
        robot = RobotBase()
        robot.close()

        with self.assertRaisesRegex(
            RobotLifecycleError,
            "robot is closed",
        ):
            robot.require_started()


class RobotBaseCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.robot = DriveRobot()

    def test_has_capability_accepts_enum(
        self,
    ) -> None:
        self.assertTrue(self.robot.has_capability(RobotCapability.DRIVE))
        self.assertFalse(self.robot.has_capability(RobotCapability.AUDIO))

    def test_has_capability_accepts_string(
        self,
    ) -> None:
        self.assertTrue(self.robot.has_capability("drive"))
        self.assertFalse(self.robot.has_capability("audio"))

    def test_has_capability_normalizes_string(
        self,
    ) -> None:
        self.assertTrue(self.robot.has_capability(" DRIVE "))

    def test_has_capability_rejects_empty_string(
        self,
    ) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "capability cannot be empty",
                ),
            ):
                self.robot.has_capability(value)

    def test_has_capability_rejects_unknown_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unknown robot capability",
        ):
            self.robot.has_capability("unknown")

    def test_has_capability_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            1,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "capability must be a RobotCapability or string",
                ),
            ):
                self.robot.has_capability(
                    value  # type: ignore[arg-type]
                )

    def test_capability_names_are_sorted(
        self,
    ) -> None:
        self.assertEqual(
            self.robot.capability_names(),
            (
                "drive",
                "system",
            ),
        )


class RobotBaseLifecycleTests(unittest.TestCase):
    def test_start(self) -> None:
        robot = RobotBase()

        robot.start()

        self.assertTrue(robot.started)
        self.assertFalse(robot.closed)

    def test_start_is_idempotent(self) -> None:
        robot = RobotBase()

        robot.start()
        robot.start()

        self.assertTrue(robot.started)

    def test_start_after_close_fails(self) -> None:
        robot = RobotBase()
        robot.close()

        with self.assertRaisesRegex(
            RobotLifecycleError,
            "robot is closed",
        ):
            robot.start()

    def test_stop_all(self) -> None:
        robot = RobotBase()
        robot.start()

        robot.stop_all()

        self.assertFalse(robot.started)
        self.assertFalse(robot.closed)

    def test_stop_all_before_start_is_allowed(
        self,
    ) -> None:
        robot = RobotBase()

        robot.stop_all()

        self.assertFalse(robot.started)

    def test_stop_all_after_close_fails(
        self,
    ) -> None:
        robot = RobotBase()
        robot.close()

        with self.assertRaisesRegex(
            RobotLifecycleError,
            "robot is closed",
        ):
            robot.stop_all()

    def test_close(self) -> None:
        robot = RobotBase()

        robot.close()

        self.assertFalse(robot.started)
        self.assertTrue(robot.closed)

    def test_close_stops_started_robot(
        self,
    ) -> None:
        robot = TrackingRobot()
        robot.start()

        robot.close()

        self.assertEqual(
            robot.stop_calls,
            1,
        )
        self.assertFalse(robot.started)
        self.assertTrue(robot.closed)

    def test_close_does_not_stop_unstarted_robot(
        self,
    ) -> None:
        robot = TrackingRobot()

        robot.close()

        self.assertEqual(
            robot.stop_calls,
            0,
        )

    def test_close_is_idempotent(self) -> None:
        robot = TrackingRobot()
        robot.start()

        robot.close()
        robot.close()

        self.assertEqual(
            robot.stop_calls,
            1,
        )
        self.assertTrue(robot.closed)

    def test_deinit_closes_robot(self) -> None:
        robot = RobotBase()
        robot.start()

        robot.deinit()

        self.assertFalse(robot.started)
        self.assertTrue(robot.closed)


class RobotBaseContextManagerTests(unittest.TestCase):
    def test_context_manager_starts_and_closes(
        self,
    ) -> None:
        robot = RobotBase()

        with robot as active:
            self.assertIs(
                active,
                robot,
            )
            self.assertTrue(robot.started)
            self.assertFalse(robot.closed)

        self.assertFalse(robot.started)
        self.assertTrue(robot.closed)

    def test_context_manager_closes_after_error(
        self,
    ) -> None:
        robot = RobotBase()

        with (
            self.assertRaisesRegex(
                RuntimeError,
                "operation failed",
            ),
            robot,
        ):
            raise RuntimeError("operation failed")

        self.assertFalse(robot.started)
        self.assertTrue(robot.closed)

    def test_closed_robot_rejects_context_entry(
        self,
    ) -> None:
        robot = RobotBase()
        robot.close()

        with (
            self.assertRaisesRegex(
                RobotLifecycleError,
                "robot is closed",
            ),
            robot,
        ):
            pass


if __name__ == "__main__":
    unittest.main()
