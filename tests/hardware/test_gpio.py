from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from betabox_robotics.hardware.gpio import (
    close_gpio_factory,
)


class CloseGPIOFactoryTests(unittest.TestCase):
    def test_no_factory_is_no_op(self) -> None:
        with patch("betabox_robotics.hardware.gpio.Device") as device:
            device.pin_factory = None

            close_gpio_factory()

        self.assertIsNone(device.pin_factory)

    def test_closes_factory_and_clears_global_reference(
        self,
    ) -> None:
        factory = MagicMock()

        with patch("betabox_robotics.hardware.gpio.Device") as device:
            device.pin_factory = factory

            close_gpio_factory()

            factory.close.assert_called_once_with()
            self.assertIsNone(device.pin_factory)

    def test_clears_reference_when_close_raises(
        self,
    ) -> None:
        factory = MagicMock()
        factory.close.side_effect = RuntimeError("close failed")

        with patch("betabox_robotics.hardware.gpio.Device") as device:
            device.pin_factory = factory

            with self.assertRaisesRegex(
                RuntimeError,
                "close failed",
            ):
                close_gpio_factory()

            self.assertIsNone(device.pin_factory)

    def test_repeated_close_is_safe(self) -> None:
        factory = MagicMock()

        with patch("betabox_robotics.hardware.gpio.Device") as device:
            device.pin_factory = factory

            close_gpio_factory()
            close_gpio_factory()

            factory.close.assert_called_once_with()
            self.assertIsNone(device.pin_factory)


if __name__ == "__main__":
    unittest.main()
