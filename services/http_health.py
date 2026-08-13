from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.client import HTTPResponse
from typing import cast


def _validate_url(
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError("url must be a string")

    result = value.strip()

    if not result:
        raise ValueError("url cannot be empty")

    return result


def _validate_timeout(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("timeout must be a number")

    result = float(value)

    if result <= 0:
        raise ValueError("timeout must be greater than 0")

    return result


def _validate_optional_service(
    value: object,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("expected_service must be a string or None")

    result = value.strip()

    if not result:
        raise ValueError("expected_service cannot be empty")

    return result


def check_http_available(
    url: str,
    *,
    timeout: float = 3.0,
) -> tuple[bool, str]:
    url_value = _validate_url(url)
    timeout_value = _validate_timeout(timeout)

    request = urllib.request.Request(
        url_value,
        method="GET",
    )

    try:
        with cast(
            HTTPResponse,
            urllib.request.urlopen(
                request,
                timeout=timeout_value,
            ),
        ) as response:
            status_code = response.status

    except urllib.error.HTTPError as exc:
        return (
            False,
            f"HTTP {exc.code}: {exc.reason}",
        )

    except urllib.error.URLError as exc:
        return (
            False,
            f"connection failed: {exc.reason}",
        )

    except TimeoutError:
        return (
            False,
            "request timed out",
        )

    except OSError as exc:
        return (
            False,
            f"request failed: {exc}",
        )

    if status_code == 200:
        return (
            True,
            "responding",
        )

    return (
        False,
        f"unexpected HTTP status {status_code}",
    )


def check_json_health(
    url: str,
    *,
    expected_service: str | None = None,
    timeout: float = 3.0,
) -> tuple[bool, str]:
    url_value = _validate_url(url)
    timeout_value = _validate_timeout(timeout)
    service_value = _validate_optional_service(expected_service)

    request = urllib.request.Request(
        url_value,
        method="GET",
        headers={
            "Accept": "application/json",
        },
    )

    try:
        with cast(
            HTTPResponse,
            urllib.request.urlopen(
                request,
                timeout=timeout_value,
            ),
        ) as response:
            status_code = response.status
            body = response.read().decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as exc:
        return (
            False,
            f"HTTP {exc.code}: {exc.reason}",
        )

    except urllib.error.URLError as exc:
        return (
            False,
            f"connection failed: {exc.reason}",
        )

    except TimeoutError:
        return (
            False,
            "request timed out",
        )

    except OSError as exc:
        return (
            False,
            f"request failed: {exc}",
        )

    if status_code != 200:
        return (
            False,
            f"unexpected HTTP status {status_code}",
        )

    try:
        raw_payload = cast(
            object,
            json.loads(body),
        )
    except json.JSONDecodeError:
        return (
            False,
            "response was not valid JSON",
        )

    if not isinstance(
        raw_payload,
        dict,
    ):
        return (
            False,
            "response JSON was not an object",
        )

    payload = cast(
        dict[object, object],
        raw_payload,
    )

    status = payload.get("status")

    if status != "ok":
        return (
            False,
            f"health status was {status if status is not None else 'missing'}",
        )

    if service_value is not None:
        service = payload.get("service")

        if service != service_value:
            return (
                False,
                "unexpected service identity: "
                + f"{service if service is not None else 'missing'}",
            )

    return (
        True,
        "healthy",
    )
