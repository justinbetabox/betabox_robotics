from __future__ import annotations

import unittest

from aiohttp import web

from betabox_robotics.calibration import CalibrationManager
from betabox_robotics.calibration.hardware import CalibrationHardware
from betabox_robotics.launchpad.drive_controller import ManualDriveController
from betabox_robotics.launchpad.services import (
    LAUNCHPAD_SERVICES_KEY,
    LaunchpadServices,
)
from betabox_robotics.launchpad.status_cache import StatusCache
from betabox_robotics.services.calibration import CalibrationService


def make_manager() -> CalibrationManager:
    return object.__new__(CalibrationManager)


def make_calibration_service() -> CalibrationService:
    return object.__new__(CalibrationService)


def make_calibration_hardware() -> CalibrationHardware:
    return object.__new__(CalibrationHardware)


def make_drive_controller() -> ManualDriveController:
    return object.__new__(ManualDriveController)


def make_services(
    *,
    drive_controller: ManualDriveController | None = None,
) -> LaunchpadServices:
    return LaunchpadServices(
        calibration_manager=make_manager(),
        calibration_service=make_calibration_service(),
        calibration_hardware=make_calibration_hardware(),
        status_cache=StatusCache(),
        drive_controller=drive_controller,
    )


class LaunchpadServicesTests(unittest.TestCase):
    def test_constructs_without_drive_controller(
        self,
    ) -> None:
        services = make_services()

        self.assertIsInstance(
            services.calibration_manager,
            CalibrationManager,
        )
        self.assertIsInstance(
            services.calibration_service,
            CalibrationService,
        )
        self.assertIsInstance(
            services.calibration_hardware,
            CalibrationHardware,
        )
        self.assertIsInstance(
            services.status_cache,
            StatusCache,
        )
        self.assertIsNone(
            services.drive_controller,
        )

    def test_constructs_with_drive_controller(
        self,
    ) -> None:
        controller = make_drive_controller()

        services = make_services(
            drive_controller=controller,
        )

        self.assertIs(
            services.drive_controller,
            controller,
        )

    def test_rejects_invalid_calibration_manager(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "calibration_manager must be a CalibrationManager",
        ):
            LaunchpadServices(
                calibration_manager=object(),  # type: ignore[arg-type]
                calibration_service=make_calibration_service(),
                calibration_hardware=make_calibration_hardware(),
                status_cache=StatusCache(),
            )

    def test_rejects_invalid_calibration_service(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "calibration_service must be a CalibrationService",
        ):
            LaunchpadServices(
                calibration_manager=make_manager(),
                calibration_service=object(),  # type: ignore[arg-type]
                calibration_hardware=make_calibration_hardware(),
                status_cache=StatusCache(),
            )

    def test_rejects_invalid_calibration_hardware(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "calibration_hardware must be a CalibrationHardware",
        ):
            LaunchpadServices(
                calibration_manager=make_manager(),
                calibration_service=make_calibration_service(),
                calibration_hardware=object(),  # type: ignore[arg-type]
                status_cache=StatusCache(),
            )

    def test_rejects_invalid_status_cache(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "status_cache must be a StatusCache",
        ):
            LaunchpadServices(
                calibration_manager=make_manager(),
                calibration_service=make_calibration_service(),
                calibration_hardware=make_calibration_hardware(),
                status_cache=object(),  # type: ignore[arg-type]
            )

    def test_rejects_invalid_drive_controller(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("drive_controller must be a ManualDriveController or None"),
        ):
            LaunchpadServices(
                calibration_manager=make_manager(),
                calibration_service=make_calibration_service(),
                calibration_hardware=make_calibration_hardware(),
                status_cache=StatusCache(),
                drive_controller=object(),  # type: ignore[arg-type]
            )

    def test_require_drive_controller_returns_controller(
        self,
    ) -> None:
        controller = make_drive_controller()
        services = make_services(
            drive_controller=controller,
        )

        self.assertIs(
            services.require_drive_controller(),
            controller,
        )

    def test_require_drive_controller_raises_when_missing(
        self,
    ) -> None:
        services = make_services()

        with self.assertRaisesRegex(
            RuntimeError,
            "Manual drive controller is not available",
        ):
            services.require_drive_controller()

    def test_is_slotted(
        self,
    ) -> None:
        services = make_services()

        self.assertFalse(
            hasattr(
                services,
                "__dict__",
            )
        )


class LaunchpadServicesKeyTests(unittest.TestCase):
    def test_key_is_app_key(
        self,
    ) -> None:
        self.assertIsInstance(
            LAUNCHPAD_SERVICES_KEY,
            web.AppKey,
        )

    def test_key_can_store_and_retrieve_services(
        self,
    ) -> None:
        app = web.Application()
        services = make_services()

        app[LAUNCHPAD_SERVICES_KEY] = services

        self.assertIs(
            app[LAUNCHPAD_SERVICES_KEY],
            services,
        )


if __name__ == "__main__":
    unittest.main()
