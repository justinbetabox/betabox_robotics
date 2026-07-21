from __future__ import annotations

import aiohttp_jinja2

from aiohttp import web


STUDENT_TOOLS = (
    {
        "title": "Manual Drive",
        "description": (
            "Control movement, steering, and the "
            "camera from your browser."
        ),
        "href": "/drive",
        "category": "Control",
        "accent": "blue",
        "action": "Open controls",
    },
    {
        "title": "Coding",
        "description": (
            "Open JupyterLab to write Python and "
            "program your robot."
        ),
        "href": "/jupyter",
        "category": "Build",
        "accent": "green",
        "action": "Open JupyterLab",
    },
    {
        "title": "Vision",
        "description": (
            "View the robot's live vision feed."
        ),
        "href": "/camera",
        "category": "Vision",
        "accent": "orange",
        "action": "View vision",
    },
    {
        "title": "Media",
        "description": (
            "Browse pictures, videos, recordings, "
            "and sounds."
        ),
        "href": "/media",
        "category": "Create",
        "accent": "pink",
        "action": "Browse media",
    },
    {
        "title": "Calibration",
        "description": (
            "Run guided calibration and hardware "
            "alignment tools."
        ),
        "href": "/calibration",
        "category": "Setup",
        "accent": "blue",
        "action": "Calibrate robot",
    },
)


INFORMATION_TOOLS = (
    {
        "title": "Status",
        "description": (
            "See detailed robot, hardware, network, "
            "and system health."
        ),
        "href": "/status",
        "category": "Understand",
        "accent": "blue",
        "action": "View status",
    },
    {
        "title": "Diagnostics",
        "description": (
            "Run Verify and Doctor to find and "
            "understand problems."
        ),
        "href": "/diagnostics",
        "category": "Troubleshoot",
        "accent": "green",
        "action": "Run checks",
    },
    {
        "title": "Services",
        "description": (
            "See which platform services are "
            "installed and running."
        ),
        "href": "/services",
        "category": "Platform",
        "accent": "orange",
        "action": "View services",
    },
    {
        "title": "Information",
        "description": (
            "View robot information and adjust "
            "your Launchpad preferences."
        ),
        "href": "/information",
        "category": "Learn",
        "accent": "pink",
        "action": "View information",
    },
    {
        "title": "Events",
        "description": (
            "Review recent robot and platform "
            "activity."
        ),
        "href": "/events",
        "category": "History",
        "accent": "blue",
        "action": "View events",
    },
)


async def home(
    request: web.Request,
) -> web.Response:
    return aiohttp_jinja2.render_template(
        "home.html",
        request,
        {
            "page": {
                "title": "Launchpad",
            },
            "student_tools": STUDENT_TOOLS,
            "information_tools": (
                INFORMATION_TOOLS
            ),
        },
    )


def setup_home_routes(
    app: web.Application,
) -> None:
    app.router.add_get(
        "/",
        home,
        name="home-page",
    )
