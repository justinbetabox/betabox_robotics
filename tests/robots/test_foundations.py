from __future__ import annotations

import unittest

from betabox_robotics.robots.capabilities import (
    RobotCapability,
)
from betabox_robotics.robots.exceptions import (
    RobotError,
    RobotLifecycleError,
)


class RobotCapabilityTests(unittest.TestCase):
    def test_values(self) -> None:
        self.assertEqual(
            RobotCapability.DRIVE.value,
            "drive",
        )
        self.assertEqual(
            RobotCapability.SENSORS.value,
            "sensors",
        )
        self.assertEqual(
            RobotCapability.VISION.value,
            "vision",
        )
        self.assertEqual(
            RobotCapability.AUDIO.value,
            "audio",
        )
        self.assertEqual(
            RobotCapability.SYSTEM.value,
            "system",
        )

    def test_members(self) -> None:
        self.assertEqual(
            tuple(RobotCapability),
            (
                RobotCapability.DRIVE,
                RobotCapability.SENSORS,
                RobotCapability.VISION,
                RobotCapability.AUDIO,
                RobotCapability.SYSTEM,
            ),
        )

    def test_constructs_from_value(self) -> None:
        self.assertIs(
            RobotCapability("drive"),
            RobotCapability.DRIVE,
        )

    def test_rejects_unknown_value(self) -> None:
        with self.assertRaises(ValueError):
            RobotCapability("unknown")

    def test_string_behavior(self) -> None:
        self.assertEqual(
            str(RobotCapability.DRIVE),
            "drive",
        )

    def test_is_string_compatible(self) -> None:
        capability = RobotCapability.VISION

        self.assertIsInstance(
            capability,
            str,
        )
        self.assertEqual(
            f"{capability}",
            "vision",
        )


class RobotExceptionTests(unittest.TestCase):
    def test_robot_error_is_exception(
        self,
    ) -> None:
        self.assertTrue(
            issubclass(
                RobotError,
                Exception,
            )
        )

    def test_lifecycle_error_inherits_robot_error(
        self,
    ) -> None:
        self.assertTrue(
            issubclass(
                RobotLifecycleError,
                RobotError,
            )
        )

    def test_lifecycle_error_can_be_caught_as_robot_error(
        self,
    ) -> None:
        with self.assertRaises(RobotError):
            raise RobotLifecycleError("robot is closed")

    def test_exception_message(self) -> None:
        error = RobotLifecycleError("robot is closed")

        self.assertEqual(
            str(error),
            "robot is closed",
        )


if __name__ == "__main__":
    unittest.main()
