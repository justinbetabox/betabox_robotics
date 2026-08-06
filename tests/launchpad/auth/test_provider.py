from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import web

from betabox_robotics.config import PlatformConfig
from betabox_robotics.launchpad.auth.context import LaunchpadContext
from betabox_robotics.launchpad.auth.provider import (
    LAUNCHPAD_CONTEXT_KEY,
    LAUNCHPAD_CONTEXT_PROVIDER_KEY,
    LaunchpadContextProvider,
    _validate_platform,
    _validate_request,
    launchpad_context_middleware,
)
from betabox_robotics.launchpad.auth.session import Session
from betabox_robotics.launchpad.auth.session_manager import (
    SESSION_MANAGER_KEY,
    SessionManager,
)
from betabox_robotics.launchpad.services import (
    LAUNCHPAD_SERVICES_KEY,
    LaunchpadServices,
)


MODULE = "betabox_robotics.launchpad.auth.provider"


def make_platform() -> PlatformConfig:
    return object.__new__(
        PlatformConfig
    )


def make_services() -> LaunchpadServices:
    return object.__new__(
        LaunchpadServices
    )


def make_session_manager() -> SessionManager:
    return SessionManager()


def make_request() -> web.Request:
    return object.__new__(
        web.Request
    )


class ValidationTests(unittest.TestCase):
    def test_validate_platform_accepts_platform(
        self,
    ) -> None:
        platform = make_platform()

        self.assertIs(
            _validate_platform(
                platform
            ),
            platform,
        )

    def test_validate_platform_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "platform must be a PlatformConfig",
        ):
            _validate_platform(
                object()
            )

    def test_validate_request_accepts_request(
        self,
    ) -> None:
        request = make_request()

        self.assertIs(
            _validate_request(
                request
            ),
            request,
        )

    def test_validate_request_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "request must be a web.Request",
        ):
            _validate_request(
                object()
            )


class ProviderConstructionTests(unittest.TestCase):
    def test_constructs_with_platform(
        self,
    ) -> None:
        platform = make_platform()

        provider = LaunchpadContextProvider(
            platform
        )

        self.assertIs(
            provider.platform,
            platform,
        )
        self.assertIs(
            provider._platform,
            platform,
        )

    def test_rejects_invalid_platform(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "platform must be a PlatformConfig",
        ):
            LaunchpadContextProvider(
                object()  # type: ignore[arg-type]
            )


class ContextTests(unittest.TestCase):
    def test_builds_context_for_resolved_session(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        session_manager = make_session_manager()
        session = Session(
            id="abc123",
            username="student1",
        )
        context = Mock(
            spec=LaunchpadContext
        )
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_SERVICES_KEY: services,
            SESSION_MANAGER_KEY: session_manager,
        }

        provider = LaunchpadContextProvider(
            platform
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ) as validate_request,
            patch.object(
                session_manager,
                "resolve",
                return_value=session,
            ) as resolve,
            patch(
                f"{MODULE}.build_account_context",
                return_value=context,
            ) as build_context,
        ):
            result = provider.context(
                request
            )

        self.assertIs(
            result,
            context,
        )
        validate_request.assert_called_once_with(
            request
        )
        resolve.assert_called_once_with(
            request
        )
        build_context.assert_called_once_with(
            platform,
            services,
            "student1",
        )

    def test_builds_guest_context_for_guest_session(
        self,
    ) -> None:
        platform = make_platform()
        services = make_services()
        session_manager = make_session_manager()
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_SERVICES_KEY: services,
            SESSION_MANAGER_KEY: session_manager,
        }

        provider = LaunchpadContextProvider(
            platform
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            patch.object(
                session_manager,
                "resolve",
                return_value=Session.guest(),
            ),
            patch(
                f"{MODULE}.build_account_context",
                return_value=Mock(
                    spec=LaunchpadContext
                ),
            ) as build_context,
        ):
            provider.context(
                request
            )

        build_context.assert_called_once_with(
            platform,
            services,
            "guest",
        )

    def test_rejects_invalid_services_wiring(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_SERVICES_KEY: object(),
            SESSION_MANAGER_KEY: make_session_manager(),
        }
        provider = LaunchpadContextProvider(
            make_platform()
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            self.assertRaisesRegex(
                TypeError,
                "Launchpad services are invalid",
            ),
        ):
            provider.context(
                request
            )

    def test_rejects_invalid_session_manager_wiring(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_SERVICES_KEY: make_services(),
            SESSION_MANAGER_KEY: object(),
        }
        provider = LaunchpadContextProvider(
            make_platform()
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            self.assertRaisesRegex(
                TypeError,
                "Session manager is invalid",
            ),
        ):
            provider.context(
                request
            )

    def test_missing_services_key_error_propagates(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.app = {
            SESSION_MANAGER_KEY: make_session_manager(),
        }
        provider = LaunchpadContextProvider(
            make_platform()
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            self.assertRaises(
                KeyError
            ),
        ):
            provider.context(
                request
            )

    def test_missing_session_manager_key_error_propagates(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_SERVICES_KEY: make_services(),
        }
        provider = LaunchpadContextProvider(
            make_platform()
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            self.assertRaises(
                KeyError
            ),
        ):
            provider.context(
                request
            )

    def test_session_resolution_error_propagates(
        self,
    ) -> None:
        services = make_services()
        session_manager = make_session_manager()
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_SERVICES_KEY: services,
            SESSION_MANAGER_KEY: session_manager,
        }
        provider = LaunchpadContextProvider(
            make_platform()
        )
        error = RuntimeError(
            "session failed"
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            patch.object(
                session_manager,
                "resolve",
                side_effect=error,
            ),
            self.assertRaises(
                RuntimeError
            ) as context,
        ):
            provider.context(
                request
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_context_build_error_propagates(
        self,
    ) -> None:
        services = make_services()
        session_manager = make_session_manager()
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_SERVICES_KEY: services,
            SESSION_MANAGER_KEY: session_manager,
        }
        provider = LaunchpadContextProvider(
            make_platform()
        )
        error = LookupError(
            "account missing"
        )

        with (
            patch(
                f"{MODULE}._validate_request",
                return_value=request,
            ),
            patch.object(
                session_manager,
                "resolve",
                return_value=Session.guest(),
            ),
            patch(
                f"{MODULE}.build_account_context",
                side_effect=error,
            ),
            self.assertRaises(
                LookupError
            ) as context,
        ):
            provider.context(
                request
            )

        self.assertIs(
            context.exception,
            error,
        )


class MiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_attaches_context_and_calls_handler(
        self,
    ) -> None:
        provider = Mock(
            spec=LaunchpadContextProvider
        )
        context = Mock(
            spec=LaunchpadContext
        )
        response = Mock(
            spec=web.StreamResponse
        )
        provider.context.return_value = context

        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_CONTEXT_PROVIDER_KEY: provider,
        }
        request.__setitem__ = Mock()
        handler = AsyncMock(
            return_value=response
        )

        result = await launchpad_context_middleware(
            request,
            handler,
        )

        self.assertIs(
            result,
            response,
        )
        provider.context.assert_called_once_with(
            request
        )
        request.__setitem__.assert_called_once_with(
            LAUNCHPAD_CONTEXT_KEY,
            context,
        )
        handler.assert_awaited_once_with(
            request
        )

    async def test_context_is_attached_before_handler(
        self,
    ) -> None:
        provider = Mock(
            spec=LaunchpadContextProvider
        )
        context = Mock(
            spec=LaunchpadContext
        )
        provider.context.return_value = context
        events: list[str] = []

        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_CONTEXT_PROVIDER_KEY: provider,
        }

        def set_item(
            key: object,
            value: object,
        ) -> None:
            events.append(
                "context"
            )

        request.__setitem__ = Mock(
            side_effect=set_item
        )

        async def handler(
            value: web.Request,
        ) -> web.StreamResponse:
            events.append(
                "handler"
            )
            return Mock(
                spec=web.StreamResponse
            )

        await launchpad_context_middleware(
            request,
            handler,
        )

        self.assertEqual(
            events,
            [
                "context",
                "handler",
            ],
        )

    async def test_rejects_invalid_provider_wiring(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_CONTEXT_PROVIDER_KEY: object(),
        }
        handler = AsyncMock()

        with self.assertRaisesRegex(
            TypeError,
            "Launchpad context provider is invalid",
        ):
            await launchpad_context_middleware(
                request,
                handler,
            )

        handler.assert_not_awaited()

    async def test_missing_provider_key_error_propagates(
        self,
    ) -> None:
        request = Mock(
            spec=web.Request
        )
        request.app = {}
        handler = AsyncMock()

        with self.assertRaises(
            KeyError
        ):
            await launchpad_context_middleware(
                request,
                handler,
            )

        handler.assert_not_awaited()

    async def test_provider_error_prevents_handler(
        self,
    ) -> None:
        provider = Mock(
            spec=LaunchpadContextProvider
        )
        provider.context.side_effect = RuntimeError(
            "context failed"
        )
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_CONTEXT_PROVIDER_KEY: provider,
        }
        handler = AsyncMock()

        with self.assertRaisesRegex(
            RuntimeError,
            "context failed",
        ):
            await launchpad_context_middleware(
                request,
                handler,
            )

        handler.assert_not_awaited()

    async def test_handler_error_propagates(
        self,
    ) -> None:
        provider = Mock(
            spec=LaunchpadContextProvider
        )
        provider.context.return_value = Mock(
            spec=LaunchpadContext
        )
        request = Mock(
            spec=web.Request
        )
        request.app = {
            LAUNCHPAD_CONTEXT_PROVIDER_KEY: provider,
        }
        request.__setitem__ = Mock()
        error = RuntimeError(
            "handler failed"
        )
        handler = AsyncMock(
            side_effect=error
        )

        with self.assertRaises(
            RuntimeError
        ) as context:
            await launchpad_context_middleware(
                request,
                handler,
            )

        self.assertIs(
            context.exception,
            error,
        )


class KeyTests(unittest.TestCase):
    def test_context_key_is_request_key(
        self,
    ) -> None:
        self.assertIsInstance(
            LAUNCHPAD_CONTEXT_KEY,
            web.RequestKey,
        )

    def test_provider_key_is_app_key(
        self,
    ) -> None:
        self.assertIsInstance(
            LAUNCHPAD_CONTEXT_PROVIDER_KEY,
            web.AppKey,
        )

    def test_provider_key_can_store_provider(
        self,
    ) -> None:
        app = web.Application()
        provider = LaunchpadContextProvider(
            make_platform()
        )

        app[
            LAUNCHPAD_CONTEXT_PROVIDER_KEY
        ] = provider

        self.assertIs(
            app[
                LAUNCHPAD_CONTEXT_PROVIDER_KEY
            ],
            provider,
        )


if __name__ == "__main__":
    unittest.main()
