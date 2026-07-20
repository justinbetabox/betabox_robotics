from .camera import setup_camera_routes
from .diagnostics import setup_diagnostics_routes
from .drive import setup_drive_routes
from .events import setup_events_routes
from .home import setup_home_routes
from .information import setup_information_routes
from .jupyter import setup_jupyter_routes
from .services import setup_services_routes
from .status import setup_status_routes
from .media import setup_media_routes


def setup_routes(
    app,
) -> None:
    setup_home_routes(app)
    setup_diagnostics_routes(app)
    setup_status_routes(app)
    setup_services_routes(app)
    setup_information_routes(app)
    setup_events_routes(app)
    setup_camera_routes(app)
    setup_jupyter_routes(app)
    setup_drive_routes(app)
    setup_media_routes(app)


__all__ = [
    "setup_camera_routes",
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
]
