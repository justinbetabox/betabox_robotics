from __future__ import annotations

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.http_health import (
    check_json_health,
)

from .models import CheckResult
from .validation import (
    validate_config,
    validate_timeout,
)


def check_launchpad(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    """
    Verify that the Launchpad service is active and its
    JSON health endpoint responds successfully.
    """

    config_value = validate_config(config)
    verification = config_value.verification
    timeout_value = validate_timeout(verification.command_timeout_seconds)
    unit = config_value.services.launchpad.unit

    service_result = run(
        [
            "systemctl",
            "is-active",
            unit,
        ],
        timeout=timeout_value,
    )

    if service_result is None:
        return CheckResult(
            name="launchpad:http",
            ok=False,
            message=f"{unit} is unknown",
        )

    service_state = (
        service_result.stdout.strip() or service_result.stderr.strip() or "unknown"
    )

    if service_result.returncode != 0:
        return CheckResult(
            name="launchpad:http",
            ok=False,
            message=(f"{unit} is {service_state}"),
        )

    ok, message = check_json_health(
        config_value.network.launchpad_health_url,
        expected_service="launchpad",
        timeout=float(timeout_value),
    )

    return CheckResult(
        name="launchpad:http",
        ok=ok,
        message=("Launchpad responding" if ok else message),
    )
