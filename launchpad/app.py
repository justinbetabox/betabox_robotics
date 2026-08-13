from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

import aiohttp_jinja2
import jinja2
from aiohttp import web

from betabox_robotics import BetaboxCar
from betabox_robotics.calibration import (
    CalibrationManager,
)
from betabox_robotics.calibration.hardware import (
    CalibrationHardware,
)
from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.launchpad.auth import (
    AUTHENTICATION_SERVICE_KEY,
    LAUNCHPAD_CONTEXT_PROVIDER_KEY,
    SESSION_MANAGER_KEY,
    AuthenticationService,
    LaunchpadContextProvider,
    SessionManager,
    launchpad_context_middleware,
    launchpad_template_context,
)
from betabox_robotics.launchpad.drive_controller import (
    ManualDriveController,
)
from betabox_robotics.launchpad.routes import (
    setup_routes,
)
from betabox_robotics.launchpad.services import (
    LAUNCHPAD_SERVICES_KEY,
    LaunchpadServices,
)
from betabox_robotics.launchpad.status_cache import (
    StatusCache,
)
from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.services.calibration import (
    CalibrationService,
)

PACKAGE_DIR = Path(__file__).parent
STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATES_DIR = PACKAGE_DIR / "templates"


async def drive_controller_context(
    app: web.Application,
) -> AsyncIterator[None]:
    services = app[LAUNCHPAD_SERVICES_KEY]

    def create_robot() -> BetaboxCar:
        calibration = services.calibration_manager.load()

        return BetaboxCar(
            calibration=calibration,
        )

    controller = ManualDriveController(create_robot)

    await controller.start()
    services.drive_controller = controller

    try:
        yield
    finally:
        services.drive_controller = None
        await controller.close()


async def health(
    _request: web.Request,
) -> web.Response:
    return web.json_response(
        {
            "service": "launchpad",
            "status": "ok",
        }
    )


def create_app(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> web.Application:
    app = web.Application(
        middlewares=[
            launchpad_context_middleware,
        ]
    )

    _ = aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        context_processors=(launchpad_template_context,),
        autoescape=jinja2.select_autoescape(
            enabled_extensions=(
                "html",
                "htm",
                "xml",
            ),
            default_for_string=True,
            default=True,
        ),
    )

    app[AUTHENTICATION_SERVICE_KEY] = AuthenticationService()

    app[SESSION_MANAGER_KEY] = SessionManager()

    app[LAUNCHPAD_CONTEXT_PROVIDER_KEY] = LaunchpadContextProvider(config)

    calibration_manager = CalibrationManager(config.paths.calibration_file)

    calibration_service = CalibrationService(calibration_manager)

    calibration_hardware = CalibrationHardware(
        drive_config=BETABOX_CAR.drive,
        camera_mount_config=BETABOX_CAR.camera_mount,
        grayscale_config=BETABOX_CAR.sensors.grayscale,
    )

    status_cache = StatusCache(ttl_seconds=3.0)

    launchpad_services = LaunchpadServices(
        calibration_manager=calibration_manager,
        calibration_service=calibration_service,
        calibration_hardware=calibration_hardware,
        status_cache=status_cache,
    )

    app[LAUNCHPAD_SERVICES_KEY] = launchpad_services

    app.cleanup_ctx.append(drive_controller_context)

    setup_routes(app)

    _ = app.router.add_static(
        "/static/",
        STATIC_DIR,
        name="static",
    )

    _ = app.router.add_get(
        "/api/health",
        health,
        name="health-api",
    )

    return app


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG

    default_host, default_port = config.network.launchpad_bind_address

    parser = argparse.ArgumentParser(prog="betabox launchpad")

    _ = parser.add_argument(
        "--host",
        default=default_host,
    )

    _ = parser.add_argument(
        "--port",
        type=int,
        default=default_port,
    )

    args = parser.parse_args(argv)

    host = cast(
        object,
        args.host,
    )

    port = cast(
        object,
        args.port,
    )

    if not isinstance(
        host,
        str,
    ):
        print("--host must be a string")
        return 1

    host = host.strip()

    if not host:
        print("--host cannot be empty")
        return 1

    if isinstance(port, bool) or not isinstance(
        port,
        int,
    ):
        print("--port must be an integer")
        return 1

    if not 1 <= port <= 65535:
        print("--port must be between 1 and 65535")
        return 1

    web.run_app(
        create_app(config),
        host=host,
        port=port,
    )

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
