from __future__ import annotations

import argparse

from collections.abc import AsyncIterator
from pathlib import Path

import aiohttp_jinja2
import jinja2

from aiohttp import web

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.launchpad.drive_controller import (
    ManualDriveController,
)
from betabox_robotics.launchpad.routes import (
    setup_routes,
)
from betabox_robotics.launchpad.status_cache import (
    StatusCache,
)
from betabox_robotics.calibration import (
    CalibrationManager,
)
from betabox_robotics.services.calibration import (
    CalibrationService,
)
from betabox_robotics.launchpad.auth import (
    LaunchpadContextProvider,
    launchpad_context_middleware
)
from betabox_robotics.launchpad.services import (
    LaunchpadServices,
)


PACKAGE_DIR = Path(__file__).parent
STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATES_DIR = PACKAGE_DIR / "templates"


async def drive_controller_context(
    app: web.Application,
) -> AsyncIterator[None]:
    services: LaunchpadServices = (
        app["launchpad_services"]
    )

    controller = ManualDriveController(
        services.calibration_manager
    )

    await controller.start()

    services.drive_controller = controller

    # Keep this temporarily for existing handlers.
    app["drive_controller"] = controller

    try:
        yield
    finally:
        services.drive_controller = None
        await controller.close()
        await controller.close()


async def health(
    request: web.Request,
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

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(
            TEMPLATES_DIR
        ),
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

    app["platform_config"] = config

    app["context_provider"] = (
        LaunchpadContextProvider(config)
    )

    calibration_manager = CalibrationManager(
        config.paths.calibration_file
    )

    calibration_service = CalibrationService(
        calibration_manager
    )

    status_cache = StatusCache(
        ttl_seconds=3.0
    )

    launchpad_services = LaunchpadServices(
        calibration_manager=calibration_manager,
        calibration_service=calibration_service,
        status_cache=status_cache,
    )

    app["launchpad_services"] = (
        launchpad_services
    )

    app["calibration_manager"] = (
        calibration_manager
    )

    app["calibration_service"] = (
        calibration_service
    )

    app["status_cache"] = StatusCache(
        ttl_seconds=3.0
    )

    app.cleanup_ctx.append(
        drive_controller_context
    )

    setup_routes(app)

    app.router.add_static(
        "/static/",
        STATIC_DIR,
        name="static",
    )

    app.router.add_get(
        "/api/health",
        health,
        name="health-api",
    )

    return app


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG

    default_host, default_port = (
        config.network.launchpad_bind_address
    )

    parser = argparse.ArgumentParser(
        prog="betabox launchpad"
    )

    parser.add_argument(
        "--host",
        default=default_host,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
    )

    args = parser.parse_args(argv)

    if not args.host:
        print("--host cannot be empty")
        return 1

    if not 1 <= args.port <= 65535:
        print(
            "--port must be between "
            "1 and 65535"
        )
        return 1

    web.run_app(
        create_app(config),
        host=args.host,
        port=args.port,
    )

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(
        main(sys.argv[1:])
    )
