from __future__ import annotations

import argparse
from pathlib import Path

from aiohttp import web

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.launchpad.routes import (
    setup_drive_routes,
    setup_home_routes,
    setup_status_routes,
)

from betabox_robotics.launchpad.drive_controller import (
    ManualDriveController,
)


STATIC_DIR = Path(__file__).parent / "static"

async def drive_controller_context(
    app: web.Application,
):
    controller = ManualDriveController()

    await controller.start()

    app["drive_controller"] = controller

    try:
        yield
    finally:
        await controller.close()

def create_app(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> web.Application:
    app = web.Application()

    app["platform_config"] = config

    app.cleanup_ctx.append(
        drive_controller_context
    )

    setup_home_routes(app)
    setup_status_routes(app)
    setup_drive_routes(app)

    app.router.add_static(
        "/static/",
        STATIC_DIR,
        name="static",
    )

    return app


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG

    parser = argparse.ArgumentParser(
        prog="betabox launchpad"
    )

    parser.add_argument(
        "--host",
        default=config.network.bind_host,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=config.network.launchpad_port,
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
