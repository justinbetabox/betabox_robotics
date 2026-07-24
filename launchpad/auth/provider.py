from __future__ import annotations

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.services import (
    LAUNCHPAD_SERVICES_KEY,
)

from .context import LaunchpadContext
from .factory import build_account_context
from .session_manager import SESSION_MANAGER_KEY


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

        services = request.app[LAUNCHPAD_SERVICES_KEY]

        session_manager = request.app[SESSION_MANAGER_KEY]

        session = session_manager.resolve(request)

        return build_account_context(
            self._platform,
            services,
            session.username,
        )


LAUNCHPAD_CONTEXT_KEY = web.RequestKey(
    "launchpad_context",
    LaunchpadContext,
)

LAUNCHPAD_CONTEXT_PROVIDER_KEY = web.AppKey(
    "launchpad_context_provider",
    LaunchpadContextProvider,
)


@web.middleware
async def launchpad_context_middleware(
    request: web.Request,
    handler: web.RequestHandler,
) -> web.StreamResponse:
    """Attach the current Launchpad context to the request."""

    provider = request.app[LAUNCHPAD_CONTEXT_PROVIDER_KEY]

    request[LAUNCHPAD_CONTEXT_KEY] = provider.context(request)

    return await handler(request)
