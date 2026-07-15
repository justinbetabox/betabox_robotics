from .drive import setup_drive_routes
from .home import setup_home_routes
from .status import setup_status_routes
from .camera import setup_camera_routes
from .jupyter import setup_jupyter_routes


__all__ = [
    "setup_drive_routes",
    "setup_home_routes",
    "setup_status_routes",
    "setup_camera_routes",
    "setup_jupyter_routes",
]
