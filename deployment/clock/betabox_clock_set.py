#!/usr/bin/python3 -I
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

MIN_TIMESTAMP_MS = 1_735_689_600_000
MAX_TIMESTAMP_MS = 4_102_444_800_000
MIN_CORRECTION_SECONDS = 60


def ntp_synchronized() -> bool:
    """Check whether the operating system has synchronized time."""

    result = subprocess.run(
        [
            "/usr/bin/timedatectl",
            "show",
            "--property=NTPSynchronized",
            "--value",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )

    value = result.stdout.strip()

    if value not in {"yes", "no"}:
        raise RuntimeError("Unable to determine NTP synchronization")

    return value == "yes"


def main() -> int:
    arguments = sys.argv[1:]
    dry_run = False

    if len(arguments) == 2 and arguments[0] == "--dry-run":
        dry_run = True
        arguments = arguments[1:]

    if len(arguments) != 1:
        print("Usage: betabox-clock-set [--dry-run] TIMESTAMP_MS")
        return 2

    timestamp = arguments[0]

    if re.fullmatch(r"[0-9]{13}", timestamp) is None:
        print("Invalid timestamp")
        return 2

    timestamp_ms = int(timestamp)

    if not MIN_TIMESTAMP_MS <= timestamp_ms < MAX_TIMESTAMP_MS:
        print("Timestamp outside permitted range")
        return 2

    current_time = time.time()
    target_time = timestamp_ms / 1000.0

    if target_time - current_time < MIN_CORRECTION_SECONDS:
        print("Clock correction not needed")
        return 0

    if ntp_synchronized():
        print("NTP synchronized; correction skipped")
        return 0

    if dry_run:
        print("Clock correction would be permitted")
        return 0

    if os.geteuid() != 0:
        print("Clock correction requires root privileges")
        return 1

    time.clock_settime(time.CLOCK_REALTIME, target_time)

    subprocess.run(
        ["/usr/sbin/fake-hwclock", "save"],
        check=True,
        timeout=5,
    )

    print("Clock corrected successfully")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(f"Clock correction failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
