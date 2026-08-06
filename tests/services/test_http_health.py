from __future__ import annotations

import json
import unittest
import urllib.error
from email.message import Message
from unittest.mock import patch

from betabox_robotics.services.http_health import (
    _validate_optional_service,
    _validate_timeout,
    _validate_url,
    check_http_available,
    check_json_health,
)

MODULE = "betabox_robotics.services.http_health"


class MockResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"",
    ) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> MockResponse:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        return None


class ValidateUrlTests(unittest.TestCase):
    def test_accepts_and_normalizes_url(self) -> None:
        self.assertEqual(
            _validate_url(" http://127.0.0.1:8080/health "),
            "http://127.0.0.1:8080/health",
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "url must be a string",
                ),
            ):
                _validate_url(value)

    def test_rejects_empty_url(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "url cannot be empty",
                ),
            ):
                _validate_url(value)


class ValidateTimeoutTests(unittest.TestCase):
    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_timeout(3),
            3.0,
        )

    def test_accepts_positive_float(self) -> None:
        self.assertEqual(
            _validate_timeout(0.5),
            0.5,
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            False,
            "3",
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "timeout must be a number",
                ),
            ):
                _validate_timeout(value)

    def test_rejects_non_positive_timeout(self) -> None:
        for value in (
            0,
            0.0,
            -1,
            -0.5,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "timeout must be greater than 0",
                ),
            ):
                _validate_timeout(value)


class ValidateOptionalServiceTests(unittest.TestCase):
    def test_accepts_none(self) -> None:
        self.assertIsNone(_validate_optional_service(None))

    def test_accepts_and_normalizes_service(self) -> None:
        self.assertEqual(
            _validate_optional_service(" launchpad "),
            "launchpad",
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("expected_service must be a string or None"),
                ),
            ):
                _validate_optional_service(value)

    def test_rejects_empty_service(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "expected_service cannot be empty",
                ),
            ):
                _validate_optional_service(value)


class CheckHttpAvailableTests(unittest.TestCase):
    def test_returns_available_for_http_200(self) -> None:
        response = MockResponse(status=200)

        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=response,
        ) as urlopen:
            result = check_http_available(
                " http://127.0.0.1:8080/health ",
                timeout=2,
            )

        self.assertEqual(
            result,
            (
                True,
                "responding",
            ),
        )

        request = urlopen.call_args.args[0]

        self.assertEqual(
            request.full_url,
            "http://127.0.0.1:8080/health",
        )
        self.assertEqual(
            request.get_method(),
            "GET",
        )
        urlopen.assert_called_once_with(
            request,
            timeout=2.0,
        )

    def test_returns_failure_for_unexpected_status(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=MockResponse(status=204),
        ):
            result = check_http_available("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "unexpected HTTP status 204",
            ),
        )

    def test_handles_http_error(self) -> None:
        error = urllib.error.HTTPError(
            url="http://127.0.0.1/health",
            code=503,
            msg="Service Unavailable",
            hdrs=Message(),
            fp=None,
        )

        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=error,
        ):
            result = check_http_available("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "HTTP 503: Service Unavailable",
            ),
        )

    def test_handles_url_error(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = check_http_available("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "connection failed: connection refused",
            ),
        )

    def test_handles_timeout(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=TimeoutError,
        ):
            result = check_http_available("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "request timed out",
            ),
        )

    def test_handles_os_error(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=OSError("network unavailable"),
        ):
            result = check_http_available("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "request failed: network unavailable",
            ),
        )

    def test_unexpected_exception_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.urllib.request.urlopen",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_http_available("http://127.0.0.1/health")

        self.assertIs(
            context.exception,
            error,
        )

    def test_validates_before_creating_request(self) -> None:
        with (
            patch(f"{MODULE}.urllib.request.Request") as request_type,
            self.assertRaisesRegex(
                ValueError,
                "url cannot be empty",
            ),
        ):
            check_http_available(" ")

        request_type.assert_not_called()

    def test_validates_timeout_before_creating_request(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.urllib.request.Request") as request_type,
            self.assertRaisesRegex(
                TypeError,
                "timeout must be a number",
            ),
        ):
            check_http_available(
                "http://127.0.0.1/health",
                timeout=True,
            )

        request_type.assert_not_called()


class CheckJsonHealthTests(unittest.TestCase):
    def test_returns_healthy_for_valid_response(self) -> None:
        response = MockResponse(
            status=200,
            body=json.dumps(
                {
                    "status": "ok",
                    "service": "launchpad",
                }
            ).encode("utf-8"),
        )

        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=response,
        ) as urlopen:
            result = check_json_health(
                " http://127.0.0.1:8081/health ",
                expected_service=" launchpad ",
                timeout=2,
            )

        self.assertEqual(
            result,
            (
                True,
                "healthy",
            ),
        )

        request = urlopen.call_args.args[0]

        self.assertEqual(
            request.full_url,
            "http://127.0.0.1:8081/health",
        )
        self.assertEqual(
            request.get_method(),
            "GET",
        )
        self.assertEqual(
            request.get_header("Accept"),
            "application/json",
        )
        urlopen.assert_called_once_with(
            request,
            timeout=2.0,
        )

    def test_service_identity_is_optional(self) -> None:
        response = MockResponse(
            status=200,
            body=b'{"status": "ok"}',
        )

        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=response,
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                True,
                "healthy",
            ),
        )

    def test_decodes_invalid_utf8_with_replacement(
        self,
    ) -> None:
        response = MockResponse(
            status=200,
            body=(b'{"status": "ok", "message": "\xff"}'),
        )

        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=response,
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                True,
                "healthy",
            ),
        )

    def test_returns_failure_for_unexpected_status(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=MockResponse(
                status=204,
                body=b'{"status": "ok"}',
            ),
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "unexpected HTTP status 204",
            ),
        )

    def test_handles_http_error(self) -> None:
        error = urllib.error.HTTPError(
            url="http://127.0.0.1/health",
            code=500,
            msg="Internal Server Error",
            hdrs=Message(),
            fp=None,
        )

        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=error,
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "HTTP 500: Internal Server Error",
            ),
        )

    def test_handles_url_error(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "connection failed: connection refused",
            ),
        )

    def test_handles_timeout(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=TimeoutError,
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "request timed out",
            ),
        )

    def test_handles_os_error(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            side_effect=OSError("network unavailable"),
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "request failed: network unavailable",
            ),
        )

    def test_unexpected_exception_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.urllib.request.urlopen",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_json_health("http://127.0.0.1/health")

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_json(self) -> None:
        response = MockResponse(
            status=200,
            body=b"{invalid json",
        )

        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=response,
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "response was not valid JSON",
            ),
        )

    def test_rejects_non_object_json(self) -> None:
        for payload in (
            [],
            [
                "ok",
            ],
            "ok",
            123,
            None,
        ):
            with (
                self.subTest(payload=payload),
                patch(
                    f"{MODULE}.urllib.request.urlopen",
                    return_value=MockResponse(
                        status=200,
                        body=json.dumps(payload).encode("utf-8"),
                    ),
                ),
            ):
                result = check_json_health("http://127.0.0.1/health")

            self.assertEqual(
                result,
                (
                    False,
                    "response JSON was not an object",
                ),
            )

    def test_rejects_missing_health_status(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=MockResponse(
                status=200,
                body=b"{}",
            ),
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "health status was missing",
            ),
        )

    def test_rejects_unhealthy_status(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=MockResponse(
                status=200,
                body=b'{"status": "error"}',
            ),
        ):
            result = check_json_health("http://127.0.0.1/health")

        self.assertEqual(
            result,
            (
                False,
                "health status was error",
            ),
        )

    def test_rejects_missing_service_identity(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=MockResponse(
                status=200,
                body=b'{"status": "ok"}',
            ),
        ):
            result = check_json_health(
                "http://127.0.0.1/health",
                expected_service="launchpad",
            )

        self.assertEqual(
            result,
            (
                False,
                "unexpected service identity: missing",
            ),
        )

    def test_rejects_wrong_service_identity(self) -> None:
        with patch(
            f"{MODULE}.urllib.request.urlopen",
            return_value=MockResponse(
                status=200,
                body=(b'{"status": "ok", "service": "video"}'),
            ),
        ):
            result = check_json_health(
                "http://127.0.0.1/health",
                expected_service="launchpad",
            )

        self.assertEqual(
            result,
            (
                False,
                "unexpected service identity: video",
            ),
        )

    def test_validates_expected_service_before_request(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.urllib.request.Request") as request_type,
            self.assertRaisesRegex(
                ValueError,
                "expected_service cannot be empty",
            ),
        ):
            check_json_health(
                "http://127.0.0.1/health",
                expected_service=" ",
            )

        request_type.assert_not_called()

    def test_validates_url_before_request(self) -> None:
        with (
            patch(f"{MODULE}.urllib.request.Request") as request_type,
            self.assertRaisesRegex(
                ValueError,
                "url cannot be empty",
            ),
        ):
            check_json_health(" ")

        request_type.assert_not_called()

    def test_validates_timeout_before_request(self) -> None:
        with (
            patch(f"{MODULE}.urllib.request.Request") as request_type,
            self.assertRaisesRegex(
                TypeError,
                "timeout must be a number",
            ),
        ):
            check_json_health(
                "http://127.0.0.1/health",
                timeout=True,
            )

        request_type.assert_not_called()


if __name__ == "__main__":
    unittest.main()
