from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PREFIX = "Betabox"


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True)


def get_serial() -> str | None:
    serial_path = Path("/sys/firmware/devicetree/base/serial-number")

    if serial_path.exists():
        serial = serial_path.read_text(errors="ignore").replace("\x00", "").strip()
        return serial or None

    cpuinfo = Path("/proc/cpuinfo")

    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="ignore").splitlines():
            if line.startswith("Serial"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip() or None

    return None


def desired_hostname(prefix: str = PREFIX) -> str | None:
    serial = get_serial()

    if not serial:
        return None

    return f"{prefix}-{serial[-4:]}"


def current_hostname() -> str:
    result = run(["hostname"])
    return result.stdout.strip()


def update_hosts_file(hostname: str, *, dry_run: bool = False) -> None:
    hosts_path = Path("/etc/hosts")

    if dry_run:
        print(f"Would update /etc/hosts 127.0.1.1 entry to {hostname}")
        return

    lines = hosts_path.read_text(errors="ignore").splitlines()
    updated = False
    new_lines: list[str] = []

    for line in lines:
        if line.startswith("127.0.1.1"):
            new_lines.append(f"127.0.1.1\t{hostname}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"127.0.1.1\t{hostname}")

    hosts_path.write_text("\n".join(new_lines) + "\n")


def set_hostname(*, prefix: str = PREFIX, dry_run: bool = False) -> int:
    new_hostname = desired_hostname(prefix)

    if not new_hostname:
        print("Could not determine serial; leaving hostname unchanged.")
        return 0

    old_hostname = current_hostname()

    if old_hostname == new_hostname:
        print(f"Hostname already correct: {old_hostname}")
        return 0

    print(f"Changing hostname from {old_hostname} to {new_hostname}")

    if dry_run:
        print(f"Would run: hostnamectl set-hostname {new_hostname}")
        update_hosts_file(new_hostname, dry_run=True)
        return 0

    result = run(["hostnamectl", "set-hostname", new_hostname])

    if result.returncode != 0:
        print(result.stderr.strip() or "hostnamectl failed")
        return result.returncode

    update_hosts_file(new_hostname)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox set-hostname")
    parser.add_argument("--prefix", default=PREFIX)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    return set_hostname(prefix=args.prefix, dry_run=args.dry_run)


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
