from __future__ import annotations

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.verify_checks import (
    CheckResult,
    collect_checks,
)
from betabox_robotics.services.verify_checks.validation import (
    validate_checks,
)


def print_results(
    checks: tuple[CheckResult, ...],
) -> bool:
    checks_value = validate_checks(checks)

    print()
    print("Betabox Verification")
    print("====================")
    print()

    all_ok = True

    for check in checks_value:
        status = "OK" if check.ok else "FAIL"

        print(f"[{status}] {check.name}")

        if check.message:
            print(f"     {check.message}")

        if not check.ok:
            all_ok = False

    print()

    if all_ok:
        print("Betabox verification passed.")
    else:
        print("Betabox verification failed.")

    return all_ok


def main() -> int:
    try:
        checks = collect_checks(
            config=DEFAULT_PLATFORM_CONFIG,
        )
    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1

    return 0 if print_results(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
