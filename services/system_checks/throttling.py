from __future__ import annotations

from betabox_robotics.services.command import run

from .models import ThrottlingStatus


def collect_throttling_status() -> ThrottlingStatus:
    """
    Collect the Raspberry Pi throttling and undervoltage status.
    """

    result = run(
        [
            "vcgencmd",
            "get_throttled",
        ],
        timeout=5,
    )

    if result is None or result.returncode != 0:
        return ThrottlingStatus(
            raw=None,
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
            error="vcgencmd get_throttled failed",
        )

    output = result.stdout.strip()

    prefix, separator, raw_value = output.partition("=")

    if not separator or prefix.strip() != "throttled" or not raw_value.strip():
        return ThrottlingStatus(
            raw=output,
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
            error="invalid vcgencmd response",
        )

    try:
        value = int(
            raw_value.strip(),
            16,
        )
    except ValueError as exc:
        return ThrottlingStatus(
            raw=output,
            undervoltage_now=False,
            undervoltage_occurred=False,
            throttled_now=False,
            throttled_occurred=False,
            error=str(exc),
        )

    return ThrottlingStatus(
        raw=f"0x{value:x}",
        undervoltage_now=bool(value & (1 << 0)),
        throttled_now=bool(value & (1 << 2)),
        undervoltage_occurred=bool(value & (1 << 16)),
        throttled_occurred=bool(value & (1 << 18)),
    )
