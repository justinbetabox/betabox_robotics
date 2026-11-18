from __future__ import annotations

import math

MIN_BROWSER_TIME_MS = 1_735_689_600_000  # January 1, 2025
MAX_BROWSER_TIME_MS = 4_102_444_800_000  # January 1, 2100

MIN_CORRECTION_SECONDS = 60


def clock_correction_target(
    browser_time_ms: object,
    system_time_seconds: float,
) -> float | None:
    """
    Return a browser-derived Unix timestamp when forward clock
    correction is appropriate.

    This function does not modify the system clock.
    """

    if isinstance(browser_time_ms, bool):
        return None

    if not isinstance(browser_time_ms, int):
        return None

    if not MIN_BROWSER_TIME_MS <= browser_time_ms < MAX_BROWSER_TIME_MS:
        return None

    if not math.isfinite(system_time_seconds):
        return None

    browser_time_seconds = browser_time_ms / 1000.0

    difference = browser_time_seconds - system_time_seconds

    if difference < MIN_CORRECTION_SECONDS:
        return None

    return browser_time_seconds
