from __future__ import annotations

import argparse
import subprocess
import time

from betabox_robotics.services.identity import (
    identity_name,
)

WIFI_IFACE = "wlan0"
ETH_IFACE = "eth0"
AP_NAME = "PiAP"
SSID_PREFIX = "Betabox"
DEFAULT_DELAY_SECONDS = 20


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


def dynamic_ssid(
    prefix: str = SSID_PREFIX,
) -> str:
    name = identity_name(
        prefix,
        fallback="UNKNOWN",
    )

    if name is None:
        raise RuntimeError(
            "failed to construct fallback SSID"
        )

    return name


def nmcli_available() -> bool:
    result = run(["which", "nmcli"], timeout=3)
    return bool(result and result.returncode == 0)


def ethernet_connected(iface: str = ETH_IFACE) -> bool:
    result = run(
        ["nmcli", "-t", "-f", "GENERAL.STATE", "device", "show", iface],
        timeout=5,
    )

    if result is None:
        return False

    return "connected" in result.stdout.lower()


def wifi_has_ip(iface: str = WIFI_IFACE) -> bool:
    result = run(
        ["nmcli", "-g", "IP4.ADDRESS", "device", "show", iface],
        timeout=5,
    )

    if result is None:
        return False

    return bool(result.stdout.strip())


def ap_connection_exists(ap_name: str = AP_NAME) -> bool:
    result = run(["nmcli", "-t", "-f", "NAME", "connection", "show"], timeout=5)

    if result is None:
        return False

    names = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return ap_name in names


def set_ap_ssid(ap_name: str, ssid: str, *, dry_run: bool = False) -> bool:
    print(f"wifi-fallback: using SSID: {ssid}")

    if dry_run:
        print(f"wifi-fallback: would set {ap_name} SSID to {ssid}")
        return True

    result = run(
        ["nmcli", "connection", "modify", ap_name, "802-11-wireless.ssid", ssid],
        timeout=10,
    )

    return bool(result and result.returncode == 0)


def start_ap(ap_name: str, *, dry_run: bool = False) -> bool:
    print(f"wifi-fallback: bringing up AP connection: {ap_name}")

    if dry_run:
        print(f"wifi-fallback: would run nmcli connection up {ap_name}")
        return True

    result = run(["nmcli", "connection", "up", ap_name], timeout=30)
    return bool(result and result.returncode == 0)


def run_wifi_fallback(
    *,
    delay_seconds: int = DEFAULT_DELAY_SECONDS,
    wifi_iface: str = WIFI_IFACE,
    eth_iface: str = ETH_IFACE,
    ap_name: str = AP_NAME,
    ssid_prefix: str = SSID_PREFIX,
    dry_run: bool = False,
) -> int:
    print(f"wifi-fallback: starting delay={delay_seconds}s")

    if not nmcli_available():
        print("wifi-fallback: nmcli not available")
        return 1

    if delay_seconds > 0:
        time.sleep(delay_seconds)

    if ethernet_connected(eth_iface):
        print("wifi-fallback: ethernet connected, exiting")
        return 0

    if wifi_has_ip(wifi_iface):
        print("wifi-fallback: wifi has IP, exiting")
        return 0

    print("wifi-fallback: wifi has no IP, will start AP")

    if not ap_connection_exists(ap_name):
        print(f"wifi-fallback: AP connection not found: {ap_name}")
        return 1

    ssid = dynamic_ssid(ssid_prefix)

    if not set_ap_ssid(ap_name, ssid, dry_run=dry_run):
        print("wifi-fallback: failed to set AP SSID")
        return 1

    if not start_ap(ap_name, dry_run=dry_run):
        print("wifi-fallback: failed to start AP")
        return 1

    print("wifi-fallback: AP started")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox wifi-fallback")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--wifi-iface", default=WIFI_IFACE)
    parser.add_argument("--eth-iface", default=ETH_IFACE)
    parser.add_argument("--ap-name", default=AP_NAME)
    parser.add_argument("--ssid-prefix", default=SSID_PREFIX)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    return run_wifi_fallback(
        delay_seconds=args.delay,
        wifi_iface=args.wifi_iface,
        eth_iface=args.eth_iface,
        ap_name=args.ap_name,
        ssid_prefix=args.ssid_prefix,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
