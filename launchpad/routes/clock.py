from __future__ import annotations

import asyncio
import time

from aiohttp import web

from betabox_robotics.services.clock_recovery import (
    clock_correction_target,
)

CLOCK_CORRECTION_ENABLED = True

CLOCK_HELPER = "/usr/local/libexec/betabox-clock-set"
CLOCK_HELPER_TIMEOUT = 10.0


async def apply_clock_correction(
    browser_time_ms: int,
) -> str:
    """Request a clock correction through the protected helper."""

    process = await asyncio.create_subprocess_exec(
        "/usr/bin/sudo",
        "-n",
        CLOCK_HELPER,
        str(browser_time_ms),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, _ = await asyncio.wait_for(
            process.communicate(),
            timeout=CLOCK_HELPER_TIMEOUT,
        )

    except TimeoutError:
        if process.returncode is None:
            process.kill()
            await process.wait()

        raise RuntimeError("Clock helper timed out")

    if process.returncode != 0:
        raise RuntimeError("Clock helper failed")

    message = stdout.decode("utf-8", errors="replace").strip()

    if message == "Clock corrected successfully":
        return "corrected"

    if message == "NTP synchronized; correction skipped":
        return "ntp_synchronized"

    if message == "Clock correction not needed":
        return "not_needed"

    raise RuntimeError("Unexpected clock helper response")


async def clock_check(
    request: web.Request,
) -> web.Response:
    """Evaluate browser time and optionally correct the system clock."""

    try:
        payload = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise web.HTTPBadRequest(text="Invalid JSON payload.")

    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(text="Expected a JSON object.")

    browser_time_ms = payload.get("browser_time_ms")

    candidate = clock_correction_target(
        browser_time_ms,
        time.time(),
    )

    result = "not_needed"

    if candidate is not None:
        result = "correction_available"

        if CLOCK_CORRECTION_ENABLED:
            try:
                result = await apply_clock_correction(browser_time_ms)
            except (OSError, RuntimeError):
                return web.json_response(
                    {
                        "status": "error",
                        "message": "Clock correction unavailable",
                    },
                    status=503,
                )

    return web.json_response(
        {
            "status": "ok",
            "correction_candidate": candidate is not None,
            "correction_result": result,
            "dry_run": not CLOCK_CORRECTION_ENABLED,
        }
    )


def setup_clock_routes(
    app: web.Application,
) -> None:
    """Register the clock recovery endpoint."""

    app.router.add_post(
        "/api/clock/check",
        clock_check,
        name="clock-check-api",
    )
