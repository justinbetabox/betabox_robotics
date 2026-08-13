from __future__ import annotations

from aiohttp import web

from .auth import setup_auth_routes
from .calibration import setup_calibration_routes
from .diagnostics import setup_diagnostics_routes
from .drive import setup_drive_routes
from .events import setup_events_routes
from .home import setup_home_routes
from .information import setup_information_routes
from .jupyter import setup_jupyter_routes
from .media import setup_media_routes
from .preferences import setup_preferences_routes
from .services import setup_services_routes
from .status import setup_status_routes
from .vision import setup_vision_routes


def setup_routes(
    app: web.Application,
) -> None:
    """Register all Launchpad routes."""

    setup_home_routes(app)

    setup_drive_routes(app)
    setup_jupyter_routes(app)
    setup_vision_routes(app)
    setup_media_routes(app)
    setup_calibration_routes(app)

    setup_status_routes(app)
    setup_diagnostics_routes(app)
    setup_services_routes(app)
    setup_information_routes(app)
    setup_events_routes(app)

    setup_auth_routes(app)
    setup_preferences_routes(app)


__all__ = [
    "setup_auth_routes",
    "setup_calibration_routes",
    "setup_diagnostics_routes",
    "setup_drive_routes",
    "setup_events_routes",
    "setup_home_routes",
    "setup_information_routes",
    "setup_jupyter_routes",
    "setup_media_routes",
    "setup_preferences_routes",
    "setup_routes",
    "setup_services_routes",
    "setup_status_routes",
    "setup_vision_routes",
]
