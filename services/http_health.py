from __future__ import annotations

import json
import urllib.error
import urllib.request


def check_http_available(
    url: str,
    *,
    timeout: float = 3.0,
) -> tuple[bool, str]:
    request = urllib.request.Request(
        url,
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            if response.status == 200:
                return True, "responding"

            return (
                False,
                f"unexpected HTTP status {response.status}",
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
        return False, "request timed out"

    except Exception as exc:
        return False, str(exc)


def check_json_health(
    url: str,
    *,
    expected_service: str | None = None,
    timeout: float = 3.0,
) -> tuple[bool, str]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
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
        return False, "request timed out"

    except Exception as exc:
        return False, str(exc)

    if status_code != 200:
        return (
            False,
            f"unexpected HTTP status {status_code}",
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return (
            False,
            "response was not valid JSON",
        )

    if not isinstance(payload, dict):
        return (
            False,
            "response JSON was not an object",
        )

    if payload.get("status") != "ok":
        return (
            False,
            "health status was "
            f"{payload.get('status', 'missing')}",
        )

    if (
        expected_service is not None
        and payload.get("service") != expected_service
    ):
        return (
            False,
            "unexpected service identity: "
            f"{payload.get('service', 'missing')}",
        )

    return True, "healthy"
