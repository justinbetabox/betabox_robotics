from __future__ import annotations

import json
import socket
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from betabox_robotics.version import __version__


@dataclass(frozen=True)
class StatusReport:
    version: str
    hostname: str
    ip_addresses: list[str]
    i2c_available: bool
    hifiberry_available: bool
    media_paths: dict[str, str]
    services: dict[str, str]
    jupyterhub_proxy_available: bool


def run(command: list[str], timeout: int = 5) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None


def hostname() -> str:
    return socket.gethostname()


def ip_addresses() -> list[str]:
    addresses: list[str] = []

    try:
        host = socket.gethostname()

        for info in socket.getaddrinfo(host, None):
            address = info[4][0]

            if not isinstance(address, str):
                continue

            if address.startswith("127."):
                continue

            if address not in addresses:
                addresses.append(address)

    except socket.gaierror:
        pass

    return addresses


def service_status(service: str) -> str:
    result = run(["systemctl", "is-active", service], timeout=3)

    if result is None:
        return "unknown"

    return result.stdout.strip() or "unknown"


def hifiberry_available() -> bool:
    result = run(["aplay", "-l"], timeout=5)

    if result is None:
        return False

    output = result.stdout + result.stderr
    return "snd_rpi_hifiberry_dac" in output or "HifiBerry" in output


def executable_available(command: str) -> bool:
    result = run(["which", command], timeout=3)
    return bool(result and result.returncode == 0)


def collect_status() -> StatusReport:
    media_root = Path.home() / "media"

    services = {
        "betabox-boot-announce.service": service_status(
            "betabox-boot-announce.service"
        ),
        "betabox-monitor.service": service_status("betabox-monitor.service"),
        "car-video-api.service": service_status("car-video-api.service"),
        "jupyterhub.service": service_status("jupyterhub.service"),
    }

    return StatusReport(
        version=__version__,
        hostname=hostname(),
        ip_addresses=ip_addresses(),
        i2c_available=Path("/dev/i2c-1").exists(),
        hifiberry_available=hifiberry_available(),
        media_paths={
            "pictures": str(media_root / "pictures"),
            "videos": str(media_root / "videos"),
            "sounds": str(media_root / "sounds"),
        },
        services=services,
        jupyterhub_proxy_available=executable_available("configurable-http-proxy"),
    )


def print_human(report: StatusReport) -> None:
    print()
    print("Betabox Status")
    print("==============")
    print()

    print("Identity")
    print("--------")
    print(f"Version:  {report.version}")
    print(f"Hostname: {report.hostname}")

    if report.ip_addresses:
        print(f"IP:       {', '.join(report.ip_addresses)}")
    else:
        print("IP:       none found")

    print()
    print("Platform")
    print("--------")
    print(f"I2C:       {'available' if report.i2c_available else 'missing'}")
    print(f"HifiBerry: {'available' if report.hifiberry_available else 'missing'}")

    print()
    print("Media")
    print("-----")
    for name, path in report.media_paths.items():
        exists = Path(path).exists()
        print(f"{name.title():8} {path} {'OK' if exists else 'MISSING'}")

    print()
    print("Services")
    print("--------")
    for service, state in report.services.items():
        print(f"{service:32} {state}")

    print()
    print("JupyterHub")
    print("----------")
    print(f"Service:  {report.services.get('jupyterhub.service', 'unknown')}")
    print(
        f"Proxy:    {'available' if report.jupyterhub_proxy_available else 'missing'}"
    )
    print("Port:     8000")

    print()


def main(argv: list[str] | None = None) -> int:
    report = collect_status()

    if argv and "--json" in argv:
        print(json.dumps(asdict(report), indent=2))
    else:
        print_human(report)

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
