from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.managed import managed_services


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_path(
    value: object,
    *,
    name: str,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string or Path")

    return Path(value).expanduser()


def _validate_lines(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("lines must be an integer")

    if value <= 0:
        raise ValueError("lines must be greater than 0")

    return value


def _validate_flag(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(f"{name} must be a boolean")

    return value


@dataclass(frozen=True, slots=True)
class LogTarget:
    name: str
    title: str
    unit: str | None
    file: Path | None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "name",
            _validate_string(
                self.name,
                name="name",
            ),
        )
        object.__setattr__(
            self,
            "title",
            _validate_string(
                self.title,
                name="title",
            ),
        )

        if self.unit is not None:
            object.__setattr__(
                self,
                "unit",
                _validate_string(
                    self.unit,
                    name="unit",
                ),
            )

        if self.file is not None:
            object.__setattr__(
                self,
                "file",
                _validate_path(
                    self.file,
                    name="file",
                ),
            )

        if self.unit is None and self.file is None:
            raise ValueError("target must define a unit or file")


def get_target(
    name: str,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> LogTarget | None:
    name_value = _validate_string(
        name,
        name="name",
    )
    config_value = _validate_config(config)

    managed = managed_services(config_value).get(name_value)

    if managed is None:
        return None

    return LogTarget(
        name=managed.name,
        title=managed.title,
        unit=managed.unit,
        file=managed.log_file,
    )


def tail_file(
    path: str | Path,
    lines: int,
) -> str:
    path_value = _validate_path(
        path,
        name="path",
    )
    lines_value = _validate_lines(lines)

    try:
        exists = path_value.exists()
    except OSError as exc:
        return f"Could not read log file: {path_value}: {exc}"

    if not exists:
        return f"Log file not found: {path_value}"

    result = run(
        [
            "tail",
            "-n",
            str(lines_value),
            str(path_value),
        ],
        timeout=10,
    )

    if result is None:
        return f"Could not read log file: {path_value}"

    if result.returncode != 0:
        return (
            result.stderr.strip()
            or result.stdout.strip()
            or (f"Could not read log file: {path_value}")
        )

    return result.stdout.strip() or "(empty)"


def journal_logs(
    unit: str,
    lines: int,
) -> str:
    unit_value = _validate_string(
        unit,
        name="unit",
    )
    lines_value = _validate_lines(lines)

    result = run(
        [
            "journalctl",
            "-u",
            unit_value,
            "-n",
            str(lines_value),
            "--no-pager",
        ],
        timeout=10,
    )

    if result is None:
        return f"Could not read journal for {unit_value}"

    output = result.stdout.strip() or result.stderr.strip()

    if result.returncode != 0:
        return output or (f"Could not read journal for {unit_value}")

    return output or "(no journal entries)"


def print_target_logs(
    target: LogTarget,
    *,
    lines: int,
    journal: bool,
    file: bool,
) -> None:
    lines_value = _validate_lines(lines)
    journal_value = _validate_flag(
        journal,
        name="journal",
    )
    file_value = _validate_flag(
        file,
        name="file",
    )

    if not journal_value and not file_value:
        raise ValueError("journal or file output must be enabled")

    print()
    print(f"Betabox Logs: {target.title}")
    print("=" * (14 + len(target.title)))
    print()

    if file_value and target.file is not None:
        print("File Log")
        print("--------")
        print(
            tail_file(
                target.file,
                lines_value,
            )
        )
        print()

    if journal_value and target.unit is not None:
        print("Systemd Journal")
        print("---------------")
        print(
            journal_logs(
                target.unit,
                lines_value,
            )
        )
        print()


def log_targets(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[LogTarget, ...]:
    config_value = _validate_config(config)

    return tuple(
        LogTarget(
            name=managed.name,
            title=managed.title,
            unit=managed.unit,
            file=managed.log_file,
        )
        for managed in managed_services(config_value).values()
    )


def print_targets(
    targets: tuple[LogTarget, ...],
) -> None:
    print()
    print("Available log targets")
    print("=====================")
    print()

    for target in targets:
        print(f"{target.name:14} {target.title}")

    print()


def parse_args(
    argv: list[str] | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> argparse.Namespace:
    config_value = _validate_config(config)

    parser = argparse.ArgumentParser(prog="betabox logs")

    _ = parser.add_argument(
        "target",
        nargs="?",
        help="Log target name",
    )
    _ = parser.add_argument(
        "-n",
        "--lines",
        type=int,
        default=(config_value.monitoring.default_log_lines),
        help="Number of lines",
    )
    _ = parser.add_argument(
        "--journal-only",
        action="store_true",
        help="Only show journal logs",
    )
    _ = parser.add_argument(
        "--file-only",
        action="store_true",
        help="Only show file logs",
    )
    _ = parser.add_argument(
        "--list",
        action="store_true",
        help="List available log targets",
    )

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG
    args = parse_args(
        argv,
        config=config,
    )

    try:
        lines = _validate_lines(
            cast(
                object,
                args.lines,
            )
        )

        journal_only = _validate_flag(
            cast(
                object,
                args.journal_only,
            ),
            name="journal_only",
        )

        file_only = _validate_flag(
            cast(
                object,
                args.file_only,
            ),
            name="file_only",
        )

        list_requested = _validate_flag(
            cast(
                object,
                args.list,
            ),
            name="list",
        )

        raw_target = cast(
            object,
            args.target,
        )

        target_name = (
            None
            if raw_target is None
            else _validate_string(
                raw_target,
                name="target",
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        print(str(exc))
        return 1

    if journal_only and file_only:
        print("--journal-only and --file-only cannot be used together")
        return 1

    try:
        targets = log_targets(config)
    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1

    if list_requested or target_name is None:
        print_targets(targets)
        return 0

    try:
        target = get_target(
            target_name,
            config,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        print(str(exc))
        return 1

    if target is None:
        print(f"Unknown log target: {target_name}")
        print_targets(targets)
        return 1

    try:
        print_target_logs(
            target,
            lines=lines,
            journal=not file_only,
            file=not journal_only,
        )
    except (
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        print(str(exc))
        return 1

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
