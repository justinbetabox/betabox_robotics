from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.services import (
    LAUNCHPAD_SERVICES_KEY,
)

from .context import LaunchpadContext
from .factory import build_account_context
from .session_manager import (
    SESSION_MANAGER_KEY,
)

RequestHandler = Callable[
    [web.Request],
    Awaitable[web.StreamResponse],
]


def _validate_platform(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("platform must be a PlatformConfig")

    return value


def _validate_request(
    value: object,
) -> web.Request:
    if not isinstance(
        value,
        web.Request,
    ):
        raise TypeError("request must be a web.Request")

    return value


class LaunchpadContextProvider:
    """Create Launchpad contexts for incoming requests."""

    _platform: PlatformConfig

    def __init__(
        self,
        platform: PlatformConfig,
    ) -> None:
        self._platform = _validate_platform(platform)

    @property
    def platform(
        self,
    ) -> PlatformConfig:
        return self._platform

    def context(
        self,
        request: web.Request,
    ) -> LaunchpadContext:
        """Return the Launchpad context for this request."""

        request_value = _validate_request(request)

        services = request_value.app[LAUNCHPAD_SERVICES_KEY]
        session_manager = request_value.app[SESSION_MANAGER_KEY]

        session = session_manager.resolve(request_value)

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
    handler: RequestHandler,
) -> web.StreamResponse:
    """Attach the current Launchpad context to the request."""

    provider = request.app[LAUNCHPAD_CONTEXT_PROVIDER_KEY]

    request[LAUNCHPAD_CONTEXT_KEY] = provider.context(request)

    return await handler(request)
