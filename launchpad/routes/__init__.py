from .camera import setup_camera_routes
from .drive import setup_drive_routes
from .home import setup_home_routes
from .information import setup_information_routes
from .jupyter import setup_jupyter_routes
from .services import setup_services_routes
from .status import setup_status_routes
from .diagnostics import setup_diagnostics_routes
from .events import setup_events_routes


__all__ = [
    "setup_camera_routes",
    "setup_drive_routes",
    "setup_home_routes",
    "setup_information_routes",
    "setup_jupyter_routes",
    "setup_services_routes",
    "setup_status_routes",
    "setup_diagnostics_routes",
    "setup_events_routes",
]
