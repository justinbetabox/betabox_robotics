from __future__ import annotations

import argparse
import json
import shutil
import socket
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.doctor import collect_diagnoses
from betabox_robotics.services.services import collect_services
from betabox_robotics.services.status import collect_status
from betabox_robotics.services.verify_checks import collect_checks
from betabox_robotics.version import __version__

SYSTEM_COMMANDS: tuple[
    tuple[str, tuple[str, ...]],
    ...,
] = (
    ("uname.txt", ("uname", "-a")),
    ("os-release.txt", ("cat", "/etc/os-release")),
    ("hostname.txt", ("hostname",)),
    ("ip-addresses.txt", ("hostname", "-I")),
    ("disk.txt", ("df", "-h")),
    ("memory.txt", ("free", "-h")),
    ("aplay.txt", ("aplay", "-l")),
)


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

    if isinstance(value, str):
        value = value.strip()

        if not value:
            raise ValueError(f"{name} cannot be empty")

    return Path(value).expanduser()


def _validate_command(
    value: object,
) -> list[str]:
    if not isinstance(
        value,
        list,
    ):
        raise TypeError("command must be a list")

    command = cast(
        list[object],
        value,
    )

    if not command:
        raise ValueError("command cannot be empty")

    return [
        _validate_string(
            item,
            name="command item",
        )
        for item in command
    ]


def _validate_report(
    value: object,
) -> SnapshotReport:
    if not isinstance(
        value,
        SnapshotReport,
    ):
        raise TypeError(
            "report must be a SnapshotReport",
        )

    return value


def _validate_snapshot_list(
    value: object,
) -> tuple[Path, ...]:
    if not isinstance(
        value,
        tuple,
    ):
        raise TypeError("snapshots must be a tuple")

    items = cast(
        tuple[object, ...],
        value,
    )

    if not all(isinstance(item, Path) for item in items):
        raise TypeError("snapshots must contain only Path values")

    return cast(
        tuple[Path, ...],
        items,
    )


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
class SnapshotReport:
    name: str
    path: str
    created_at: str
    hostname: str
    sdk_version: str

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
            "path",
            str(
                _validate_path(
                    self.path,
                    name="path",
                )
            ),
        )
        object.__setattr__(
            self,
            "created_at",
            _validate_string(
                self.created_at,
                name="created_at",
            ),
        )
        object.__setattr__(
            self,
            "hostname",
            _validate_string(
                self.hostname,
                name="hostname",
            ),
        )
        object.__setattr__(
            self,
            "sdk_version",
            _validate_string(
                self.sdk_version,
                name="sdk_version",
            ),
        )


def timestamp() -> str:
    value = time.strftime("%Y%m%d-%H%M%S")

    return _validate_string(
        value,
        name="timestamp",
    )


def write_text(
    path: str | Path,
    content: str,
) -> None:
    path_value = _validate_path(
        path,
        name="path",
    )
    content_value = _validate_string(
        content,
        name="content",
    )

    path_value.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    _ = path_value.write_text(
        content_value,
        encoding="utf-8",
    )


def write_json(
    path: str | Path,
    data: object,
) -> None:
    path_value = _validate_path(
        path,
        name="path",
    )

    if data is None:
        raise ValueError("data cannot be None")

    content = json.dumps(
        data,
        indent=2,
        default=str,
    )

    path_value.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    _ = path_value.write_text(
        content,
        encoding="utf-8",
    )


def command_output(
    command: list[str],
) -> str:
    command_value = _validate_command(command)

    result = run(command_value)

    if result is None:
        return "command failed to run"

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        return stderr or stdout or (f"command exited with status {result.returncode}")

    return stdout or stderr or "(no output)"


def copy_if_exists(
    source: str | Path,
    destination: str | Path,
) -> bool:
    source_value = _validate_path(
        source,
        name="source",
    )
    destination_value = _validate_path(
        destination,
        name="destination",
    )

    try:
        if not source_value.exists():
            return False

        destination_value.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if source_value.is_dir():
            _ = shutil.copytree(
                source_value,
                destination_value,
                dirs_exist_ok=True,
            )
        else:
            _ = shutil.copy2(
                source_value,
                destination_value,
            )

    except OSError:
        return False

    return True


def build_snapshot_report(
    name: str | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> SnapshotReport:
    config_value = _validate_config(config)

    if name is None:
        snapshot_name = f"snapshot-{timestamp()}"
    else:
        snapshot_name = _validate_string(
            name,
            name="name",
        )

    snapshot_dir = config_value.paths.snapshot_root / snapshot_name

    created_at = _validate_string(
        time.strftime("%Y-%m-%d %H:%M:%S"),
        name="created_at",
    )
    hostname_value = _validate_string(
        socket.gethostname(),
        name="hostname",
    )

    return SnapshotReport(
        name=snapshot_name,
        path=str(snapshot_dir),
        created_at=created_at,
        hostname=hostname_value,
        sdk_version=_validate_string(
            __version__,
            name="sdk_version",
        ),
    )


def write_manifest(
    report: SnapshotReport,
) -> None:
    report = _validate_report(
        report,
    )

    snapshot_dir = Path(report.path)

    write_json(
        snapshot_dir / "manifest.json",
        asdict(report),
    )


def write_system_reports(
    snapshot_dir: str | Path,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    snapshot_dir_value = _validate_path(
        snapshot_dir,
        name="snapshot_dir",
    )
    config_value = _validate_config(
        config,
    )

    system_dir = snapshot_dir_value / "system"

    for filename, command in SYSTEM_COMMANDS:
        write_text(
            system_dir / filename,
            command_output(
                list(command),
            ),
        )

    write_text(
        system_dir / "i2cdetect.txt",
        command_output(
            [
                "i2cdetect",
                "-y",
                str(config_value.verification.i2c_bus),
            ],
        ),
    )


def write_log_reports(
    snapshot_dir: str | Path,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    snapshot_dir_value = _validate_path(
        snapshot_dir,
        name="snapshot_dir",
    )
    config_value = _validate_config(
        config,
    )

    logs_dir = snapshot_dir_value / "logs"

    _ = copy_if_exists(
        config_value.paths.monitor_log,
        logs_dir / "monitor.log",
    )

    _ = copy_if_exists(
        config_value.paths.boot_announce_log,
        logs_dir / "boot_announce.log",
    )

    journal_targets = (
        (
            "journal-betabox-monitor.txt",
            config_value.services.monitor.unit,
        ),
        (
            "journal-boot-announce.txt",
            config_value.services.boot_announce.unit,
        ),
    )

    for filename, unit in journal_targets:
        write_text(
            logs_dir / filename,
            command_output(
                [
                    "journalctl",
                    "-u",
                    unit,
                    "-n",
                    "100",
                    "--no-pager",
                ],
            ),
        )


def write_platform_reports(
    snapshot_dir: str | Path,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> None:
    snapshot_dir_value = _validate_path(
        snapshot_dir,
        name="snapshot_dir",
    )
    config_value = _validate_config(config)

    write_json(
        snapshot_dir_value / "status.json",
        asdict(collect_status(config_value)),
    )
    write_json(
        snapshot_dir_value / "services.json",
        [asdict(item) for item in collect_services(config_value)],
    )
    write_json(
        snapshot_dir_value / "verify.json",
        [asdict(item) for item in collect_checks(config=config_value)],
    )
    write_json(
        snapshot_dir_value / "doctor.json",
        [asdict(item) for item in collect_diagnoses(config_value)],
    )


def create_snapshot(
    name: str | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> SnapshotReport:
    config_value = _validate_config(
        config,
    )

    report = build_snapshot_report(
        name,
        config=config_value,
    )

    snapshot_dir = Path(
        report.path,
    )

    if snapshot_dir.exists():
        raise FileExistsError(
            str(snapshot_dir),
        )

    write_manifest(
        report,
    )

    write_platform_reports(
        snapshot_dir,
        config=config_value,
    )

    write_system_reports(
        snapshot_dir,
        config=config_value,
    )

    write_log_reports(
        snapshot_dir,
        config=config_value,
    )

    return report


def list_snapshots(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> tuple[Path, ...]:
    config_value = _validate_config(
        config,
    )

    snapshot_root = config_value.paths.snapshot_root

    try:
        if not snapshot_root.exists():
            return ()
    except OSError:
        return ()

    return tuple(
        sorted(
            (path for path in snapshot_root.iterdir() if path.is_dir()),
            reverse=True,
        )
    )


def print_report(
    report: SnapshotReport,
) -> None:
    report = _validate_report(
        report,
    )

    print()
    print("Betabox Snapshot")
    print("================")
    print()
    print(f"Name:    {report.name}")
    print(f"Path:    {report.path}")
    print(f"Created: {report.created_at}")
    print(f"Host:    {report.hostname}")
    print(f"SDK:     {report.sdk_version}")
    print()


def print_snapshots(
    snapshots: tuple[Path, ...],
) -> None:
    snapshots = _validate_snapshot_list(
        snapshots,
    )

    print()
    print("Betabox Snapshots")
    print("=================")
    print()

    if not snapshots:
        print("No snapshots found.")
        print()
        return

    for snapshot in snapshots:
        print(snapshot.name)

    print()


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="betabox snapshot",
    )

    _ = parser.add_argument(
        "--list",
        action="store_true",
        help="List existing snapshots",
    )

    _ = parser.add_argument(
        "--name",
        help="Optional snapshot name",
    )

    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(
        argv,
    )

    try:
        list_requested = _validate_flag(
            cast(
                object,
                args.list,
            ),
            name="list",
        )

        raw_name = cast(
            object,
            args.name,
        )

        name = (
            None
            if raw_name is None
            else _validate_string(
                raw_name,
                name="name",
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        print(str(exc))
        return 1

    if list_requested:
        print_snapshots(
            list_snapshots(),
        )
        return 0

    try:
        report = create_snapshot(
            name,
        )
    except FileExistsError:
        display_name = name if name is not None else "generated snapshot name"

        print(f"Snapshot already exists: {display_name}")
        return 1

    print_report(
        report,
    )
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
