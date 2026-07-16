from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.robots.betabox_car import (
    BetaboxCar,
)


class BetaboxCarTests(unittest.TestCase):
    def test_failed_construction_releases_ownership(
        self,
    ) -> None:
        ownership = MagicMock()

        with (
            patch(
                "betabox_robotics.robots.betabox_car."
                "RobotOwnership",
                return_value=ownership,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "Drive.default",
                side_effect=RuntimeError(
                    "drive construction failed"
                ),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "drive construction failed",
            ):
                BetaboxCar()

        ownership.acquire.assert_called_once_with()
        ownership.release.assert_called_once_with()

    def test_close_releases_ownership(
        self,
    ) -> None:
        ownership = MagicMock()

        drive = MagicMock()
        sensors = MagicMock()
        camera_mount = MagicMock()
        vision = MagicMock()
        audio = MagicMock()
        system = MagicMock()

        with (
            patch(
                "betabox_robotics.robots.betabox_car."
                "RobotOwnership",
                return_value=ownership,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "Drive.default",
                return_value=drive,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "Sensors.default",
                return_value=sensors,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "CameraMount.default",
                return_value=camera_mount,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "VisionClient.default",
                return_value=vision,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "Audio.default",
                return_value=audio,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "System.default",
                return_value=system,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "close_gpio_factory"
            ) as close_gpio_factory,
        ):
            car = BetaboxCar()
            car.close()

        ownership.acquire.assert_called_once_with()
        ownership.release.assert_called_once_with()
        close_gpio_factory.assert_called_once_with()

    def test_close_is_idempotent(
        self,
    ) -> None:
        ownership = MagicMock()

        with (
            patch(
                "betabox_robotics.robots.betabox_car."
                "RobotOwnership",
                return_value=ownership,
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "Drive.default",
                return_value=MagicMock(),
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "Sensors.default",
                return_value=MagicMock(),
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "CameraMount.default",
                return_value=MagicMock(),
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "VisionClient.default",
                return_value=MagicMock(),
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "Audio.default",
                return_value=MagicMock(),
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "System.default",
                return_value=MagicMock(),
            ),
            patch(
                "betabox_robotics.robots.betabox_car."
                "close_gpio_factory"
            ) as close_gpio_factory,
        ):
            car = BetaboxCar()

            car.close()
            car.close()

        ownership.release.assert_called_once_with()
        close_gpio_factory.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
