from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from betabox_robotics.services.doctor import collect_diagnoses
from betabox_robotics.services.services import collect_services
from betabox_robotics.services.status import collect_status
from betabox_robotics.services.verify import collect_checks
from betabox_robotics.version import __version__

SNAPSHOT_ROOT = Path.home() / "betabox-snapshots"
STATE_DIR = Path.home() / ".local" / "state" / "betabox"


@dataclass(frozen=True)
class SnapshotReport:
    name: str
    path: str
    created_at: str
    hostname: str
    sdk_version: str


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


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def command_output(command: list[str]) -> str:
    result = run(command)

    if result is None:
        return "command failed to run"

    return (result.stdout + result.stderr).strip()


def copy_if_exists(source: Path, destination: Path) -> None:
    if not source.exists():
        return

    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source, destination)


def create_snapshot(name: str | None = None) -> SnapshotReport:
    snapshot_name = name or f"snapshot-{timestamp()}"
    snapshot_dir = SNAPSHOT_ROOT / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    report = SnapshotReport(
        name=snapshot_name,
        path=str(snapshot_dir),
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        hostname=socket.gethostname(),
        sdk_version=__version__,
    )

    write_json(snapshot_dir / "manifest.json", asdict(report))

    write_json(snapshot_dir / "status.json", asdict(collect_status()))
    write_json(
        snapshot_dir / "services.json", [asdict(item) for item in collect_services()]
    )
    write_json(
        snapshot_dir / "verify.json", [asdict(item) for item in collect_checks()]
    )
    write_json(
        snapshot_dir / "doctor.json", [asdict(item) for item in collect_diagnoses()]
    )

    write_text(snapshot_dir / "system" / "uname.txt", command_output(["uname", "-a"]))
    write_text(
        snapshot_dir / "system" / "os-release.txt",
        command_output(["cat", "/etc/os-release"]),
    )
    write_text(snapshot_dir / "system" / "hostname.txt", command_output(["hostname"]))
    write_text(
        snapshot_dir / "system" / "ip-addresses.txt", command_output(["hostname", "-I"])
    )
    write_text(snapshot_dir / "system" / "disk.txt", command_output(["df", "-h"]))
    write_text(snapshot_dir / "system" / "memory.txt", command_output(["free", "-h"]))
    write_text(snapshot_dir / "system" / "aplay.txt", command_output(["aplay", "-l"]))
    write_text(
        snapshot_dir / "system" / "i2cdetect.txt",
        command_output(["i2cdetect", "-y", "1"]),
    )

    logs_dir = snapshot_dir / "logs"
    copy_if_exists(STATE_DIR / "monitor.log", logs_dir / "monitor.log")
    copy_if_exists(STATE_DIR / "boot_announce.log", logs_dir / "boot_announce.log")

    write_text(
        logs_dir / "journal-betabox-monitor.txt",
        command_output(
            ["journalctl", "-u", "betabox-monitor.service", "-n", "100", "--no-pager"]
        ),
    )
    write_text(
        logs_dir / "journal-boot-announce.txt",
        command_output(
            [
                "journalctl",
                "-u",
                "betabox-boot-announce.service",
                "-n",
                "100",
                "--no-pager",
            ]
        ),
    )

    return report


def list_snapshots() -> list[Path]:
    if not SNAPSHOT_ROOT.exists():
        return []

    return sorted(
        [path for path in SNAPSHOT_ROOT.iterdir() if path.is_dir()],
        reverse=True,
    )


def print_report(report: SnapshotReport) -> None:
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


def print_snapshots(snapshots: list[Path]) -> None:
    print()
    print("Betabox Snapshots")
    print("=================")
    print()

    if not snapshots:
        print("No snapshots found.")
        print()
        return

    for path in snapshots:
        print(path.name)

    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox snapshot")
    parser.add_argument("--list", action="store_true", help="List existing snapshots")
    parser.add_argument("--name", help="Optional snapshot name")

    args = parser.parse_args(argv)

    if args.list:
        print_snapshots(list_snapshots())
        return 0

    try:
        report = create_snapshot(args.name)
    except FileExistsError:
        print(f"Snapshot already exists: {args.name}")
        return 1

    print_report(report)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
