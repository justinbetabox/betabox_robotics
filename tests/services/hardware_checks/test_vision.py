from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.hardware_checks.vision import (
    _validate_config,
    collect_vision_status,
)
from betabox_robotics.vision import VisionClientError

MODULE = "betabox_robotics.services.hardware_checks.vision"


class ValidateConfigTests(unittest.TestCase):
    def test_accepts_platform_config(self) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_rejects_invalid_config(self) -> None:
        for value in (
            None,
            object(),
            "config",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "config must be a PlatformConfig",
                ),
            ):
                _validate_config(value)


class CollectVisionStatusTests(unittest.TestCase):
    def test_creates_client_with_configured_url_and_timeout(
        self,
    ) -> None:
        statistics = SimpleNamespace(
            running=True,
            camera=SimpleNamespace(
                running=True,
                has_frame=True,
            ),
            streaming=SimpleNamespace(
                clients=2,
            ),
        )

        with patch(f"{MODULE}.VisionClient") as client_type:
            client_type.return_value.statistics.return_value = statistics

            status = collect_vision_status()

        client_type.assert_called_once_with(
            base_url=(DEFAULT_PLATFORM_CONFIG.network.vision_url),
            timeout=float(DEFAULT_PLATFORM_CONFIG.verification.command_timeout_seconds),
        )
        (client_type.return_value.statistics.assert_called_once_with())

        self.assertTrue(status.service_available)
        self.assertTrue(status.running)
        self.assertTrue(status.camera_running)
        self.assertTrue(status.camera_has_frame)
        self.assertEqual(
            status.clients,
            2,
        )
        self.assertIsNone(status.error)

    def test_reports_stopped_service_statistics(self) -> None:
        statistics = SimpleNamespace(
            running=False,
            camera=SimpleNamespace(
                running=False,
                has_frame=False,
            ),
            streaming=SimpleNamespace(
                clients=0,
            ),
        )

        with patch(f"{MODULE}.VisionClient") as client_type:
            client_type.return_value.statistics.return_value = statistics

            status = collect_vision_status()

        self.assertTrue(status.service_available)
        self.assertFalse(status.running)
        self.assertFalse(status.camera_running)
        self.assertFalse(status.camera_has_frame)
        self.assertEqual(
            status.clients,
            0,
        )
        self.assertIsNone(status.error)

    def test_preserves_independent_camera_state(self) -> None:
        statistics = SimpleNamespace(
            running=True,
            camera=SimpleNamespace(
                running=True,
                has_frame=False,
            ),
            streaming=SimpleNamespace(
                clients=3,
            ),
        )

        with patch(f"{MODULE}.VisionClient") as client_type:
            client_type.return_value.statistics.return_value = statistics

            status = collect_vision_status()

        self.assertTrue(status.service_available)
        self.assertTrue(status.running)
        self.assertTrue(status.camera_running)
        self.assertFalse(status.camera_has_frame)
        self.assertEqual(
            status.clients,
            3,
        )

    def test_handles_vision_client_error(self) -> None:
        error = VisionClientError("connection refused")

        with patch(f"{MODULE}.VisionClient") as client_type:
            (client_type.return_value.statistics.side_effect) = error

            status = collect_vision_status()

        self.assertFalse(status.service_available)
        self.assertFalse(status.running)
        self.assertFalse(status.camera_running)
        self.assertFalse(status.camera_has_frame)
        self.assertEqual(
            status.clients,
            0,
        )
        self.assertEqual(
            status.error,
            "connection refused",
        )

    def test_unexpected_client_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with patch(f"{MODULE}.VisionClient") as client_type:
            (client_type.return_value.statistics.side_effect) = error

            with self.assertRaises(RuntimeError) as context:
                collect_vision_status()

        self.assertIs(
            context.exception,
            error,
        )

    def test_client_construction_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("invalid client setup")

        with (
            patch(
                f"{MODULE}.VisionClient",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_vision_status()

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_config_before_client_creation(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.VisionClient") as client_type,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_vision_status(
                object()  # type: ignore[arg-type]
            )

        client_type.assert_not_called()

    def test_statistics_values_are_forwarded_without_coercion(
        self,
    ) -> None:
        statistics = SimpleNamespace(
            running=1,
            camera=SimpleNamespace(
                running=0,
                has_frame=1,
            ),
            streaming=SimpleNamespace(
                clients=4,
            ),
        )

        with patch(f"{MODULE}.VisionClient") as client_type:
            client_type.return_value.statistics.return_value = statistics

            status = collect_vision_status()

        self.assertEqual(
            status.running,
            1,
        )
        self.assertEqual(
            status.camera_running,
            0,
        )
        self.assertEqual(
            status.camera_has_frame,
            1,
        )
        self.assertEqual(
            status.clients,
            4,
        )


if __name__ == "__main__":
    unittest.main()
