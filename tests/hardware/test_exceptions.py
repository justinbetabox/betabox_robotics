from __future__ import annotations

import unittest

from betabox_robotics.hardware.exceptions import (
    HardwareError,
    InvalidModeError,
    InvalidPinError,
    PinModeError,
)


class HardwareExceptionTests(unittest.TestCase):
    def test_specialized_errors_inherit_hardware_error(
        self,
    ) -> None:
        for error_type in (
            InvalidPinError,
            InvalidModeError,
            PinModeError,
        ):
            with self.subTest(
                error_type=error_type,
            ):
                self.assertTrue(
                    issubclass(
                        error_type,
                        HardwareError,
                    )
                )
