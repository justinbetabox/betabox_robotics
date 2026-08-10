from __future__ import annotations

import unittest
from unittest.mock import Mock, call, patch

from aiohttp import web
from betabox_robotics.launchpad.routes import (
    __all__,
    setup_routes,
)

MODULE = "betabox_robotics.launchpad.routes"

SETUP_FUNCTIONS = (
    "setup_home_routes",
    "setup_drive_routes",
    "setup_jupyter_routes",
    "setup_vision_routes",
    "setup_media_routes",
    "setup_calibration_routes",
    "setup_status_routes",
    "setup_diagnostics_routes",
    "setup_services_routes",
    "setup_information_routes",
    "setup_events_routes",
    "setup_auth_routes",
)


def make_app() -> web.Application:
    return web.Application()


class SetupRoutesTests(unittest.TestCase):
    def test_registers_every_route_group(
        self,
    ) -> None:
        app = make_app()

        patches = [patch(f"{MODULE}.{name}") for name in SETUP_FUNCTIONS]

        mocks = [patcher.start() for patcher in patches]

        try:
            setup_routes(app)
        finally:
            for patcher in reversed(patches):
                patcher.stop()

        for name, route_mock in zip(
            SETUP_FUNCTIONS,
            mocks,
            strict=True,
        ):
            with self.subTest(
                setup_function=name,
            ):
                route_mock.assert_called_once_with(app)

    def test_registers_route_groups_in_expected_order(
        self,
    ) -> None:
        app = make_app()
        parent = Mock()

        with (
            patch(
                f"{MODULE}.setup_home_routes",
                parent.home,
            ),
            patch(
                f"{MODULE}.setup_drive_routes",
                parent.drive,
            ),
            patch(
                f"{MODULE}.setup_jupyter_routes",
                parent.jupyter,
            ),
            patch(
                f"{MODULE}.setup_vision_routes",
                parent.vision,
            ),
            patch(
                f"{MODULE}.setup_media_routes",
                parent.media,
            ),
            patch(
                f"{MODULE}.setup_calibration_routes",
                parent.calibration,
            ),
            patch(
                f"{MODULE}.setup_status_routes",
                parent.status,
            ),
            patch(
                f"{MODULE}.setup_diagnostics_routes",
                parent.diagnostics,
            ),
            patch(
                f"{MODULE}.setup_services_routes",
                parent.services,
            ),
            patch(
                f"{MODULE}.setup_information_routes",
                parent.information,
            ),
            patch(
                f"{MODULE}.setup_events_routes",
                parent.events,
            ),
            patch(
                f"{MODULE}.setup_auth_routes",
                parent.auth,
            ),
        ):
            setup_routes(app)

        self.assertEqual(
            parent.mock_calls,
            [
                call.home(app),
                call.drive(app),
                call.jupyter(app),
                call.vision(app),
                call.media(app),
                call.calibration(app),
                call.status(app),
                call.diagnostics(app),
                call.services(app),
                call.information(app),
                call.events(app),
                call.auth(app),
            ],
        )

    def test_home_routes_are_registered_first(
        self,
    ) -> None:
        app = make_app()
        parent = Mock()

        with (
            patch(
                f"{MODULE}.setup_home_routes",
                parent.home,
            ),
            patch(
                f"{MODULE}.setup_drive_routes",
                parent.drive,
            ),
            patch(
                f"{MODULE}.setup_jupyter_routes",
                parent.jupyter,
            ),
            patch(
                f"{MODULE}.setup_vision_routes",
                parent.vision,
            ),
            patch(
                f"{MODULE}.setup_media_routes",
                parent.media,
            ),
            patch(
                f"{MODULE}.setup_calibration_routes",
                parent.calibration,
            ),
            patch(
                f"{MODULE}.setup_status_routes",
                parent.status,
            ),
            patch(
                f"{MODULE}.setup_diagnostics_routes",
                parent.diagnostics,
            ),
            patch(
                f"{MODULE}.setup_services_routes",
                parent.services,
            ),
            patch(
                f"{MODULE}.setup_information_routes",
                parent.information,
            ),
            patch(
                f"{MODULE}.setup_events_routes",
                parent.events,
            ),
            patch(
                f"{MODULE}.setup_auth_routes",
                parent.auth,
            ),
        ):
            setup_routes(app)

        self.assertEqual(
            parent.mock_calls[0],
            call.home(app),
        )

    def test_auth_routes_are_registered_last(
        self,
    ) -> None:
        app = make_app()
        parent = Mock()

        with (
            patch(
                f"{MODULE}.setup_home_routes",
                parent.home,
            ),
            patch(
                f"{MODULE}.setup_drive_routes",
                parent.drive,
            ),
            patch(
                f"{MODULE}.setup_jupyter_routes",
                parent.jupyter,
            ),
            patch(
                f"{MODULE}.setup_vision_routes",
                parent.vision,
            ),
            patch(
                f"{MODULE}.setup_media_routes",
                parent.media,
            ),
            patch(
                f"{MODULE}.setup_calibration_routes",
                parent.calibration,
            ),
            patch(
                f"{MODULE}.setup_status_routes",
                parent.status,
            ),
            patch(
                f"{MODULE}.setup_diagnostics_routes",
                parent.diagnostics,
            ),
            patch(
                f"{MODULE}.setup_services_routes",
                parent.services,
            ),
            patch(
                f"{MODULE}.setup_information_routes",
                parent.information,
            ),
            patch(
                f"{MODULE}.setup_events_routes",
                parent.events,
            ),
            patch(
                f"{MODULE}.setup_auth_routes",
                parent.auth,
            ),
        ):
            setup_routes(app)

        self.assertEqual(
            parent.mock_calls[-1],
            call.auth(app),
        )

    def test_returns_none(
        self,
    ) -> None:
        app = make_app()

        with (
            patch(f"{MODULE}.{SETUP_FUNCTIONS[0]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[1]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[2]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[3]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[4]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[5]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[6]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[7]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[8]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[9]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[10]}"),
            patch(f"{MODULE}.{SETUP_FUNCTIONS[11]}"),
        ):
            result = setup_routes(app)

        self.assertIsNone(result)

    def test_rejects_invalid_application(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "app must be a web.Application",
        ):
            setup_routes(
                object()  # type: ignore[arg-type]
            )

    def test_validation_occurs_before_registration(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.setup_home_routes") as home,
            self.assertRaisesRegex(
                TypeError,
                "app must be a web.Application",
            ),
        ):
            setup_routes(
                object()  # type: ignore[arg-type]
            )

        home.assert_not_called()

    def test_registration_error_propagates_and_stops_sequence(
        self,
    ) -> None:
        app = make_app()
        error = RuntimeError("drive setup failed")

        with (
            patch(f"{MODULE}.setup_home_routes") as home,
            patch(
                f"{MODULE}.setup_drive_routes",
                side_effect=error,
            ) as drive,
            patch(f"{MODULE}.setup_jupyter_routes") as jupyter,
            self.assertRaises(RuntimeError) as context,
        ):
            setup_routes(app)

        self.assertIs(
            context.exception,
            error,
        )
        home.assert_called_once_with(app)
        drive.assert_called_once_with(app)
        jupyter.assert_not_called()


class ExportTests(unittest.TestCase):
    def test_public_exports(
        self,
    ) -> None:
        self.assertEqual(
            __all__,
            [
                "setup_auth_routes",
                "setup_calibration_routes",
                "setup_vision_routes",
                "setup_diagnostics_routes",
                "setup_drive_routes",
                "setup_events_routes",
                "setup_home_routes",
                "setup_information_routes",
                "setup_jupyter_routes",
                "setup_media_routes",
                "setup_routes",
                "setup_services_routes",
                "setup_status_routes",
            ],
        )

    def test_exports_are_unique(
        self,
    ) -> None:
        self.assertEqual(
            len(__all__),
            len(set(__all__)),
        )


if __name__ == "__main__":
    unittest.main()
