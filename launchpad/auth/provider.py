from __future__ import annotations

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.services import (
    LaunchpadServices,
)

from .context import LaunchpadContext
from .factory import build_guest_context


class LaunchpadContextProvider:
    """Creates Launchpad contexts for incoming requests."""

    def __init__(
        self,
        platform: PlatformConfig,
    ) -> None:
        self._platform = platform

    def context(
        self,
        request: web.Request,
    ) -> LaunchpadContext:
        """Return the Launchpad context for this request."""

        services: LaunchpadServices = (
            request.app["launchpad_services"]
        )

        return build_guest_context(
            self._platform,
            services,
        )


@web.middleware
async def launchpad_context_middleware(
    request: web.Request,
    handler: web.RequestHandler,
) -> web.StreamResponse:
    """Attach the current Launchpad context to the request."""

    provider: LaunchpadContextProvider = (
        request.app["context_provider"]
    )

    request["launchpad_context"] = (
        provider.context(request)
    )

    return await handler(request)
