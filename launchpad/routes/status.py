from __future__ import annotations

import asyncio
import json

from dataclasses import asdict
from pathlib import Path

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.services.http_health import (
    check_http_available,
)
from betabox_robotics.services.status import (
    collect_status,
)


ROBOT_LOCK_PATH = Path(
    "/tmp/betabox-robot.lock"
)


def read_robot_ownership() -> dict[str, object]:
    """
    Read informational robot ownership metadata.

    The lock file may exist even when no process currently holds the
    flock, so metadata alone must not be treated as authoritative.
    """

    try:
        if not ROBOT_LOCK_PATH.exists():
            return {
                "available": True,
                "owner": None,
            }

        text = ROBOT_LOCK_PATH.read_text(
            encoding="utf-8",
        ).strip()

        if not text:
            return {
                "available": True,
                "owner": None,
            }

        payload = json.loads(text)

        if not isinstance(payload, dict):
            return {
                "available": True,
                "owner": None,
            }

        owner = payload.get("owner")

        return {
            "available": not bool(owner),
            "owner": owner,
            "pid": payload.get("pid"),
            "acquired_at": payload.get(
                "acquired_at"
            ),
        }

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
    ):
        return {
            "available": True,
            "owner": None,
        }


async def status_api(
    request: web.Request,
) -> web.Response:
    config: PlatformConfig = request.app[
        "platform_config"
    ]

    report = await asyncio.to_thread(
        collect_status,
        config,
    )

    ownership = await asyncio.to_thread(
        read_robot_ownership
    )

    jupyter_state = report.services.get(
        config.services.jupyterhub,
        "unknown",
    )

    jupyter_responding = False
    jupyter_message = (
        "service is not active"
    )

    if jupyter_state == "active":
        (
            jupyter_responding,
            jupyter_message,
        ) = await asyncio.to_thread(
            check_http_available,
            config.network.jupyterhub_health_url,
        )

    payload = asdict(report)

    payload["control"] = ownership

    payload["jupyterhub"] = {
        "state": jupyter_state,
        "active": (
            jupyter_state == "active"
        ),
        "responding": jupyter_responding,
        "message": jupyter_message,
    }

    return web.json_response(
        payload
    )


def setup_status_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/api/status",
        status_api,
    )
