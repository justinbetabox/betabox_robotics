from __future__ import annotations

import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pamela

from betabox_robotics.launchpad.auth.pam_helper import (
    _validate_string,
    authenticate,
    main,
    read_request,
)


MODULE = "betabox_robotics.launchpad.auth.pam_helper"


def make_account(
    *,
    username: str = "student1",
    persistent: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        username=username,
        persistent=persistent,
    )


class ValidateStringTests(unittest.TestCase):
    def test_strips_by_default(
        self,
    ) -> None:
        self.assertEqual(
            _validate_string(
                " student1 ",
                name="username",
            ),
            "student1",
        )

    def test_preserves_value_when_strip_is_false(
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

    def test_rejects_non_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "Invalid authentication request",
        ):
            _validate_string(
                1,
                name="username",
            )

    def test_rejects_empty_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Invalid authentication request",
        ):
            _validate_string(
                " ",
                name="username",
            )

    def test_strip_false_allows_whitespace_only_value(
        self,
    ) -> None:
        self.assertEqual(
            _validate_string(
                " ",
                name="password",
                strip=False,
            ),
            " ",
        )


class ReadRequestTests(unittest.TestCase):
    def test_reads_valid_request(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "username": " student1 ",
                    "password": " password ",
                }
            )
        )

        with patch(
            f"{MODULE}.sys.stdin",
            stream,
        ):
            result = read_request()

        self.assertEqual(
            result,
            (
                "student1",
                " password ",
            ),
        )

    def test_rejects_invalid_json(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.sys.stdin",
                io.StringIO("{invalid"),
            ),
            self.assertRaisesRegex(
                ValueError,
                "Invalid authentication request",
            ),
        ):
            read_request()

    def test_rejects_non_dictionary_payload(
        self,
    ) -> None:
        for payload in (
            [],
            "value",
            1,
            None,
        ):
            with (
                self.subTest(payload=payload),
                patch(
                    f"{MODULE}.sys.stdin",
                    io.StringIO(
                        json.dumps(payload)
                    ),
                ),
                self.assertRaisesRegex(
                    TypeError,
                    "Invalid authentication request",
                ),
            ):
                read_request()

    def test_rejects_missing_username(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "password": "password",
                }
            )
        )

        with (
            patch(
                f"{MODULE}.sys.stdin",
                stream,
            ),
            self.assertRaisesRegex(
                TypeError,
                "Invalid authentication request",
            ),
        ):
            read_request()

    def test_rejects_missing_password(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "username": "student1",
                }
            )
        )

        with (
            patch(
                f"{MODULE}.sys.stdin",
                stream,
            ),
            self.assertRaisesRegex(
                TypeError,
                "Invalid authentication request",
            ),
        ):
            read_request()

    def test_rejects_non_string_username(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "username": 1,
                    "password": "password",
                }
            )
        )

        with (
            patch(
                f"{MODULE}.sys.stdin",
                stream,
            ),
            self.assertRaisesRegex(
                TypeError,
                "Invalid authentication request",
            ),
        ):
            read_request()

    def test_rejects_non_string_password(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "username": "student1",
                    "password": 1,
                }
            )
        )

        with (
            patch(
                f"{MODULE}.sys.stdin",
                stream,
            ),
            self.assertRaisesRegex(
                TypeError,
                "Invalid authentication request",
            ),
        ):
            read_request()

    def test_rejects_empty_username(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "username": " ",
                    "password": "password",
                }
            )
        )

        with (
            patch(
                f"{MODULE}.sys.stdin",
                stream,
            ),
            self.assertRaisesRegex(
                ValueError,
                "Invalid authentication request",
            ),
        ):
            read_request()

    def test_rejects_empty_password(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "username": "student1",
                    "password": "",
                }
            )
        )

        with (
            patch(
                f"{MODULE}.sys.stdin",
                stream,
            ),
            self.assertRaisesRegex(
                ValueError,
                "Invalid authentication request",
            ),
        ):
            read_request()

    def test_preserves_whitespace_only_password(
        self,
    ) -> None:
        stream = io.StringIO(
            json.dumps(
                {
                    "username": "student1",
                    "password": " ",
                }
            )
        )

        with patch(
            f"{MODULE}.sys.stdin",
            stream,
        ):
            result = read_request()

        self.assertEqual(
            result,
            (
                "student1",
                " ",
            ),
        )

    def test_converts_json_load_os_error_to_value_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.json.load",
                side_effect=OSError(
                    "read failed"
                ),
            ),
            self.assertRaisesRegex(
                ValueError,
                "Invalid authentication request",
            ) as context,
        ):
            read_request()

        self.assertIsNone(
            context.exception.__cause__,
        )


class AuthenticateTests(unittest.TestCase):
    def test_authenticates_persistent_account(
        self,
    ) -> None:
        account = make_account()

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ) as lookup,
            patch(
                f"{MODULE}.pamela.authenticate"
            ) as pam_authenticate,
        ):
            result = authenticate(
                " student1 ",
                " password ",
            )

        self.assertTrue(result)
        lookup.assert_called_once_with(
            "student1"
        )
        pam_authenticate.assert_called_once_with(
            "student1",
            " password ",
            service="login",
        )

    def test_uses_canonical_account_username(
        self,
    ) -> None:
        account = make_account(
            username="Student1"
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=account,
            ),
            patch(
                f"{MODULE}.pamela.authenticate"
            ) as pam_authenticate,
        ):
            result = authenticate(
                "student1",
                "password",
            )

        self.assertTrue(result)
        pam_authenticate.assert_called_once_with(
            "Student1",
            "password",
            service="login",
        )

    def test_rejects_invalid_direct_inputs(
        self,
    ) -> None:
        cases = (
            (
                1,
                "password",
            ),
            (
                "student1",
                1,
            ),
            (
                "",
                "password",
            ),
            (
                "student1",
                "",
            ),
        )

        for username, password in cases:
            with (
                self.subTest(
                    username=username,
                    password=password,
                ),
                patch(
                    f"{MODULE}.account_by_username"
                ) as lookup,
            ):
                result = authenticate(
                    username,  # type: ignore[arg-type]
                    password,  # type: ignore[arg-type]
                )

                self.assertFalse(result)
                lookup.assert_not_called()

    def test_unknown_account_returns_false(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username",
                side_effect=LookupError(
                    "missing"
                ),
            ),
            patch(
                f"{MODULE}.pamela.authenticate"
            ) as pam_authenticate,
        ):
            result = authenticate(
                "missing",
                "password",
            )

        self.assertFalse(result)
        pam_authenticate.assert_not_called()

    def test_nonpersistent_account_returns_false(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(
                    username="guest",
                    persistent=False,
                ),
            ),
            patch(
                f"{MODULE}.pamela.authenticate"
            ) as pam_authenticate,
        ):
            result = authenticate(
                "guest",
                "password",
            )

        self.assertFalse(result)
        pam_authenticate.assert_not_called()

    def test_pam_failure_returns_false(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            patch(
                f"{MODULE}.pamela.authenticate",
                side_effect=pamela.PAMError(
                    "authentication failed"
                ),
            ),
        ):
            result = authenticate(
                "student1",
                "wrong",
            )

        self.assertFalse(result)

    def test_unexpected_pam_error_propagates(
        self,
    ) -> None:
        error = RuntimeError(
            "programming error"
        )

        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            patch(
                f"{MODULE}.pamela.authenticate",
                side_effect=error,
            ),
            self.assertRaises(
                RuntimeError
            ) as context,
        ):
            authenticate(
                "student1",
                "password",
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_whitespace_only_password_is_preserved(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.account_by_username",
                return_value=make_account(),
            ),
            patch(
                f"{MODULE}.pamela.authenticate"
            ) as pam_authenticate,
        ):
            result = authenticate(
                "student1",
                " ",
            )

        self.assertTrue(result)
        pam_authenticate.assert_called_once_with(
            "student1",
            " ",
            service="login",
        )


class MainTests(unittest.TestCase):
    def test_returns_zero_for_success(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.read_request",
                return_value=(
                    "student1",
                    "password",
                ),
            ) as read,
            patch(
                f"{MODULE}.authenticate",
                return_value=True,
            ) as authenticate_call,
        ):
            result = main()

        self.assertEqual(
            result,
            0,
        )
        read.assert_called_once_with()
        authenticate_call.assert_called_once_with(
            "student1",
            "password",
        )

    def test_returns_one_for_failed_authentication(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.read_request",
                return_value=(
                    "student1",
                    "wrong",
                ),
            ),
            patch(
                f"{MODULE}.authenticate",
                return_value=False,
            ),
        ):
            result = main()

        self.assertEqual(
            result,
            1,
        )

    def test_returns_one_for_value_error_request(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.read_request",
                side_effect=ValueError(
                    "invalid"
                ),
            ),
            patch(
                f"{MODULE}.authenticate"
            ) as authenticate_call,
        ):
            result = main()

        self.assertEqual(
            result,
            1,
        )
        authenticate_call.assert_not_called()

    def test_returns_one_for_type_error_request(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.read_request",
                side_effect=TypeError(
                    "invalid"
                ),
            ),
            patch(
                f"{MODULE}.authenticate"
            ) as authenticate_call,
        ):
            result = main()

        self.assertEqual(
            result,
            1,
        )
        authenticate_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
