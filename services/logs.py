from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.managed import managed_services


@dataclass(frozen=True)
class LogTarget:
    name: str
    title: str
    unit: str | None
    file: Path | None


def run(command: list[str], timeout: int = 10) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None


def get_target(
    name: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> LogTarget | None:
    managed = managed_services(config).get(name)

    if managed is None:
        return None

    return LogTarget(
        name=managed.name,
        title=managed.title,
        unit=managed.unit,
        file=managed.log_file,
    )


def tail_file(path: Path, lines: int) -> str:
    if not path.exists():
        return f"Log file not found: {path}"

    result = run(["tail", "-n", str(lines), str(path)])

    if result is None:
        return f"Could not read log file: {path}"

    return result.stdout.strip() or "(empty)"


def journal_logs(unit: str, lines: int) -> str:
    result = run(
        [
            "journalctl",
            "-u",
            unit,
            "-n",
            str(lines),
            "--no-pager",
        ],
        timeout=10,
    )

    if result is None:
        return f"Could not read journal for {unit}"

    output = result.stdout.strip() or result.stderr.strip()
    return output or "(no journal entries)"


def print_target_logs(
    target: LogTarget, *, lines: int, journal: bool, file: bool
) -> None:
    print()
    print(f"Betabox Logs: {target.title}")
    print("=" * (14 + len(target.title)))
    print()

    if file and target.file is not None:
        print("File Log")
        print("--------")
        print(tail_file(target.file, lines))
        print()

    if journal and target.unit is not None:
        print("Systemd Journal")
        print("---------------")
        print(journal_logs(target.unit, lines))
        print()


def list_targets(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    print()
    print("Available log targets")
    print("=====================")
    print()

    for name, managed in managed_services(config).items():
        print(f"{name:14} {managed.title}")

    print()


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG

    parser = argparse.ArgumentParser(
        prog="betabox logs"
    )

    parser.add_argument(
        "target",
        nargs="?",
        help="Log target name",
    )

    parser.add_argument(
        "-n",
        "--lines",
        type=int,
        default=config.monitoring.default_log_lines,
        help="Number of lines",
    )

    parser.add_argument(
        "--journal-only",
        action="store_true",
        help="Only show journal logs",
    )

    parser.add_argument(
        "--file-only",
        action="store_true",
        help="Only show file logs",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available log targets",
    )

    args = parser.parse_args(argv)

    if args.lines <= 0:
        print("--lines must be greater than 0")
        return 1

    if args.list or not args.target:
        list_targets(config)
        return 0

    target = get_target(
        args.target,
        config,
    )

    if target is None:
        print(
            f"Unknown log target: "
            f"{args.target}"
        )
        list_targets(config)
        return 1

    show_journal = not args.file_only
    show_file = not args.journal_only

    print_target_logs(
        target,
        lines=args.lines,
        journal=show_journal,
        file=show_file,
    )

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
