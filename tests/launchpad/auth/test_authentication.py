from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

from aiohttp import web

from betabox_robotics.launchpad.auth.authentication import (
    AUTHENTICATION_SERVICE_KEY,
    AUTH_HELPER,
    AuthenticationError,
    AuthenticationService,
    _validate_auth_runner,
    _validate_string,
)


MODULE = "betabox_robotics.launchpad.auth.authentication"


def make_account(
    *,
    username: str = "student1",
    persistent: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        username=username,
        persistent=persistent,
    )


class ValidationTests(unittest.TestCase):
    def test_validate_string_strips_by_default(
        self,
    ) -> None:
        self.assertEqual(
            _validate_string(
                " student1 ",
                name="username",
            ),
            "student1",
        )

    def test_validate_string_preserves_password_whitespace(
        self,
    ) -> None:
        self.assertEqual(
            _validate_string(
                " password ",
                name="password",
                strip=False,
            ),
            " password ",
        )

    def test_validate_string_rejects_non_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "username must be a string",
        ):
            _validate_string(
                1,
                name="username",
            )

    def test_validate_string_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "username cannot be empty",
        ):
            _validate_string(
                " ",
                name="username",
            )

    def test_validate_auth_runner_accepts_callable(
        self,
    ) -> None:
        async def runner(
            username: str,
            password: str,
        ) -> bool:
            return True

        self.assertIs(
            _validate_auth_runner(runner),
            runner,
        )

    def test_validate_auth_runner_rejects_non_callable(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "authenticate must be callable",
        ):
            _validate_auth_runner(
                object()
            )


class AuthenticationServiceConstructionTests(unittest.TestCase):
    def test_uses_injected_runner(
        self,
    ) -> None:
        runner = AsyncMock(
            return_value=True,
        )

        service = AuthenticationService(
            runner
        )

        self.assertIs(
            service._authenticate,
            runner,
        )

    def test_uses_helper_runner_by_default(
        self,
    ) -> None:
        service = AuthenticationService()

        self.assertEqual(
            service._authenticate,
            service._authenticate_with_helper,
        )

    def test_rejects_invalid_runner(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "authenticate must be callable",
        ):
            AuthenticationService(
                object()  # type: ignore[arg-type]
            )


class AuthenticateTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticates_persistent_account(
        self,
    ) -> None:
        runner = AsyncMock(
            return_value=True,
        )
        service = AuthenticationService(
            runner
        )
        account = make_account()

        with patch(
            f"{MODULE}.account_by_username",
            return_value=account,
        ) as lookup:
            result = await service.authenticate(
                " student1 ",
                " password ",
            )

        self.assertIsNone(result)
        lookup.assert_called_once_with(
            "student1"
        )
        runner.assert_awaited_once_with(
            "student1",
            " password ",
        )

    async def test_uses_canonical_account_username(
        self,
    ) -> None:
        runner = AsyncMock(
            return_value=True,
        )
        service = AuthenticationService(
            runner
        )
        account = make_account(
            username="Student1"
        )

        with patch(
            f"{MODULE}.account_by_username",
            return_value=account,
        ):
            await service.authenticate(
                "student1",
                "password",
            )

        runner.assert_awaited_once_with(
            "Student1",
            "password",
        )

    async def test_rejects_empty_username(
        self,
    ) -> None:
        runner = AsyncMock()
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username"
            ) as lookup,
            self.assertRaisesRegex(
                AuthenticationError,
                "Username and password are required.",
            ),
        ):
            await service.authenticate(
                " ",
                "password",
            )

        lookup.assert_not_called()
        runner.assert_not_awaited()

    async def test_rejects_empty_password(
        self,
    ) -> None:
        runner = AsyncMock()
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username"
            ) as lookup,
            self.assertRaisesRegex(
                AuthenticationError,
                "Username and password are required.",
            ),
        ):
            await service.authenticate(
                "student1",
                "",
            )

        lookup.assert_not_called()
        runner.assert_not_awaited()

    async def test_whitespace_only_password_is_allowed(
        self,
    ) -> None:
        runner = AsyncMock(
            return_value=True,
        )
        service = AuthenticationService(
            runner
        )

        with patch(
            f"{MODULE}.account_by_username",
            return_value=make_account(),
        ):
            await service.authenticate(
                "student1",
                " ",
            )

        runner.assert_awaited_once_with(
            "student1",
            " ",
        )

    async def test_rejects_non_string_credentials(
        self,
    ) -> None:
        service = AuthenticationService(
            AsyncMock()
        )

        cases = (
            (
                1,
                "password",
            ),
            (
                "student1",
                1,
            ),
        )

        for username, password in cases:
            with (
                self.subTest(
                    username=username,
                    password=password,
                ),
                self.assertRaisesRegex(
                    AuthenticationError,
                    "Username and password are required.",
                ),
            ):
                await service.authenticate(
                    username,  # type: ignore[arg-type]
                    password,  # type: ignore[arg-type]
                )

    async def test_unknown_account_uses_generic_error(
        self,
    ) -> None:
        runner = AsyncMock()
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                side_effect=LookupError(
                    "missing"
                ),
            ),
            self.assertRaisesRegex(
                AuthenticationError,
                "Invalid username or password.",
            ) as context,
        ):
            await service.authenticate(
                "missing",
                "password",
            )

        self.assertIsInstance(
            context.exception.__cause__,
            LookupError,
        )
        runner.assert_not_awaited()

    async def test_rejects_nonpersistent_account(
        self,
    ) -> None:
        runner = AsyncMock()
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(
                    username="guest",
                    persistent=False,
                ),
            ),
            self.assertRaisesRegex(
                AuthenticationError,
                "Invalid username or password.",
            ),
        ):
            await service.authenticate(
                "guest",
                "password",
            )

        runner.assert_not_awaited()

    async def test_rejects_invalid_password(
        self,
    ) -> None:
        runner = AsyncMock(
            return_value=False,
        )
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            self.assertRaisesRegex(
                AuthenticationError,
                "Invalid username or password.",
            ),
        ):
            await service.authenticate(
                "student1",
                "wrong",
            )

        runner.assert_awaited_once_with(
            "student1",
            "wrong",
        )

    async def test_wraps_os_error_as_service_unavailable(
        self,
    ) -> None:
        runner = AsyncMock(
            side_effect=OSError(
                "helper unavailable"
            ),
        )
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            self.assertRaisesRegex(
                AuthenticationError,
                "Authentication service is unavailable.",
            ) as context,
        ):
            await service.authenticate(
                "student1",
                "password",
            )

        self.assertIsInstance(
            context.exception.__cause__,
            OSError,
        )

    async def test_wraps_runtime_error_as_service_unavailable(
        self,
    ) -> None:
        runner = AsyncMock(
            side_effect=RuntimeError(
                "helper missing"
            ),
        )
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            self.assertRaisesRegex(
                AuthenticationError,
                "Authentication service is unavailable.",
            ),
        ):
            await service.authenticate(
                "student1",
                "password",
            )

    async def test_cancellation_propagates(
        self,
    ) -> None:
        runner = AsyncMock(
            side_effect=asyncio.CancelledError
        )
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            self.assertRaises(
                asyncio.CancelledError
            ),
        ):
            await service.authenticate(
                "student1",
                "password",
            )

    async def test_rejects_non_boolean_runner_result(
        self,
    ) -> None:
        runner = AsyncMock(
            return_value=1,
        )
        service = AuthenticationService(
            runner
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            self.assertRaisesRegex(
                TypeError,
                "authentication runner must return a boolean",
            ),
        ):
            await service.authenticate(
                "student1",
                "password",
            )


class HelperAuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_missing_helper(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "is_file",
                return_value=False,
            ),
            patch(
                f"{MODULE}.asyncio.create_subprocess_exec"
            ) as create_process,
            self.assertRaisesRegex(
                RuntimeError,
                "authentication helper not found",
            ),
        ):
            await AuthenticationService._authenticate_with_helper(
                "student1",
                "password",
            )

        create_process.assert_not_called()

    async def test_runs_helper_and_returns_true(
        self,
    ) -> None:
        process = Mock()
        process.returncode = 0
        process.communicate = AsyncMock(
            return_value=(
                b"",
                b"",
            )
        )

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                f"{MODULE}.asyncio.create_subprocess_exec",
                new=AsyncMock(
                    return_value=process
                ),
            ) as create_process,
        ):
            result = (
                await AuthenticationService
                ._authenticate_with_helper(
                    " student1 ",
                    " password ",
                )
            )

        self.assertTrue(result)
        create_process.assert_awaited_once_with(
            "sudo",
            "-n",
            str(AUTH_HELPER),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        expected_payload = json.dumps(
            {
                "username": "student1",
                "password": " password ",
            },
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )
        process.communicate.assert_awaited_once_with(
            expected_payload
        )

    async def test_nonzero_exit_returns_false(
        self,
    ) -> None:
        process = Mock()
        process.returncode = 1
        process.communicate = AsyncMock()

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                f"{MODULE}.asyncio.create_subprocess_exec",
                new=AsyncMock(
                    return_value=process
                ),
            ),
        ):
            result = (
                await AuthenticationService
                ._authenticate_with_helper(
                    "student1",
                    "password",
                )
            )

        self.assertFalse(result)

    async def test_validates_helper_username(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                f"{MODULE}.asyncio.create_subprocess_exec"
            ) as create_process,
            self.assertRaisesRegex(
                ValueError,
                "username cannot be empty",
            ),
        ):
            await AuthenticationService._authenticate_with_helper(
                " ",
                "password",
            )

        create_process.assert_not_called()

    async def test_validates_helper_password(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                f"{MODULE}.asyncio.create_subprocess_exec"
            ) as create_process,
            self.assertRaisesRegex(
                ValueError,
                "password cannot be empty",
            ),
        ):
            await AuthenticationService._authenticate_with_helper(
                "student1",
                "",
            )

        create_process.assert_not_called()

    async def test_cancellation_kills_running_process(
        self,
    ) -> None:
        process = Mock()
        process.returncode = None
        process.communicate = AsyncMock(
            side_effect=asyncio.CancelledError
        )
        process.kill = Mock()
        process.wait = AsyncMock()

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                f"{MODULE}.asyncio.create_subprocess_exec",
                new=AsyncMock(
                    return_value=process
                ),
            ),
            self.assertRaises(
                asyncio.CancelledError
            ),
        ):
            await AuthenticationService._authenticate_with_helper(
                "student1",
                "password",
            )

        process.kill.assert_called_once_with()
        process.wait.assert_awaited_once_with()

    async def test_cancellation_does_not_kill_exited_process(
        self,
    ) -> None:
        process = Mock()
        process.returncode = 1
        process.communicate = AsyncMock(
            side_effect=asyncio.CancelledError
        )
        process.kill = Mock()
        process.wait = AsyncMock()

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                f"{MODULE}.asyncio.create_subprocess_exec",
                new=AsyncMock(
                    return_value=process
                ),
            ),
            self.assertRaises(
                asyncio.CancelledError
            ),
        ):
            await AuthenticationService._authenticate_with_helper(
                "student1",
                "password",
            )

        process.kill.assert_not_called()
        process.wait.assert_not_awaited()


class AuthenticationServiceKeyTests(unittest.TestCase):
    def test_key_is_app_key(
        self,
    ) -> None:
        self.assertIsInstance(
            AUTHENTICATION_SERVICE_KEY,
            web.AppKey,
        )

    def test_key_can_store_and_retrieve_service(
        self,
    ) -> None:
        app = web.Application()
        service = AuthenticationService(
            AsyncMock(
                return_value=True,
            )
        )

        app[AUTHENTICATION_SERVICE_KEY] = service

        self.assertIs(
            app[AUTHENTICATION_SERVICE_KEY],
            service,
        )


if __name__ == "__main__":
    unittest.main()
