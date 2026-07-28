from __future__ import annotations

import argparse
import subprocess
import time

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.identity import (
    identity_name,
)


def run(
    command: list[str],
    timeout: int = 10,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None


def wait_for_wifi_ip(
    iface: str,
    *,
    timeout_seconds: int = 5,
    poll_interval: float = 0.5,
) -> bool:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if wifi_has_ip(iface):
            return True

        time.sleep(poll_interval)

    return wifi_has_ip(iface)


def dynamic_ssid(prefix: str) -> str:
    name = identity_name(
        prefix,
        fallback="UNKNOWN",
    )

    if name is None:
        raise RuntimeError("failed to construct fallback SSID")

    return name


def nmcli_available() -> bool:
    result = run(
        ["which", "nmcli"],
        timeout=3,
    )

    return bool(result and result.returncode == 0)


def command_error(
    result: subprocess.CompletedProcess[str] | None,
) -> str:
    if result is None:
        return "command could not be executed"

    stderr = result.stderr.strip()
    stdout = result.stdout.strip()

    return stderr or stdout or (f"command exited with status {result.returncode}")


def wifi_radio_enabled() -> bool:
    result = run(
        [
            "nmcli",
            "-t",
            "-f",
            "WIFI",
            "general",
        ],
        timeout=5,
    )

    return bool(
        result and result.returncode == 0 and result.stdout.strip() == "enabled"
    )


def enable_wifi_radio(
    *,
    dry_run: bool = False,
) -> bool:
    if wifi_radio_enabled():
        return True

    print("wifi-fallback: Wi-Fi radio is disabled, enabling it")

    if dry_run:
        print("wifi-fallback: would unblock and enable Wi-Fi")
        return True

    unblock_result = run(
        [
            "rfkill",
            "unblock",
            "wifi",
        ],
        timeout=5,
    )

    if unblock_result is not None and unblock_result.returncode != 0:
        print(f"wifi-fallback: rfkill unblock failed: {command_error(unblock_result)}")

    enable_result = run(
        [
            "nmcli",
            "radio",
            "wifi",
            "on",
        ],
        timeout=10,
    )

    if enable_result is None or enable_result.returncode != 0:
        print(
            "wifi-fallback: failed to enable "
            f"Wi-Fi radio: {command_error(enable_result)}"
        )
        return False

    if not wifi_radio_enabled():
        print("wifi-fallback: Wi-Fi radio remains disabled")
        return False

    print("wifi-fallback: Wi-Fi radio was disabled; successfully re-enabled")
    return True


def ethernet_connected(
    iface: str,
) -> bool:
    result = run(
        [
            "nmcli",
            "-g",
            "GENERAL.STATE",
            "device",
            "show",
            iface,
        ],
        timeout=5,
    )

    if result is None or result.returncode != 0:
        return False

    state = result.stdout.strip()

    return state.startswith("100")


def wifi_has_ip(iface: str) -> bool:
    result = run(
        [
            "nmcli",
            "-g",
            "IP4.ADDRESS",
            "device",
            "show",
            iface,
        ],
        timeout=5,
    )

    if result is None:
        return False

    return bool(result.stdout.strip())


def ap_connection_exists(
    ap_name: str,
) -> bool:
    result = run(
        [
            "nmcli",
            "-t",
            "-f",
            "NAME",
            "connection",
            "show",
        ],
        timeout=5,
    )

    if result is None:
        return False

    names = {line.strip() for line in result.stdout.splitlines() if line.strip()}

    return ap_name in names


def set_ap_ssid(
    ap_name: str,
    ssid: str,
    *,
    dry_run: bool = False,
) -> bool:
    print(f"wifi-fallback: using SSID: {ssid}")

    if dry_run:
        print(f"wifi-fallback: would set {ap_name} SSID to {ssid}")
        return True

    result = run(
        [
            "nmcli",
            "connection",
            "modify",
            ap_name,
            "802-11-wireless.ssid",
            ssid,
        ],
        timeout=10,
    )

    if result is None or result.returncode != 0:
        print(f"wifi-fallback: failed to set AP SSID: {command_error(result)}")
        return False

    return True


def start_ap(
    ap_name: str,
    *,
    dry_run: bool = False,
) -> bool:
    print(f"wifi-fallback: bringing up AP connection: {ap_name}")

    if dry_run:
        print(f"wifi-fallback: would run nmcli connection up {ap_name}")
        return True

    result = run(
        [
            "nmcli",
            "connection",
            "up",
            ap_name,
        ],
        timeout=30,
    )

    if result is None or result.returncode != 0:
        print(f"wifi-fallback: AP activation failed: {command_error(result)}")
        return False

    return True


def run_wifi_fallback(
    *,
    delay_seconds: int | None = None,
    wifi_iface: str | None = None,
    eth_iface: str | None = None,
    ap_name: str | None = None,
    ssid_prefix: str | None = None,
    dry_run: bool = False,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> int:
    network = config.network

    selected_delay = (
        network.wifi_fallback_delay_seconds if delay_seconds is None else delay_seconds
    )

    selected_wifi_iface = network.wifi_interface if wifi_iface is None else wifi_iface

    selected_eth_iface = network.ethernet_interface if eth_iface is None else eth_iface

    selected_ap_name = network.ap_connection_name if ap_name is None else ap_name

    selected_ssid_prefix = (
        network.identity_prefix if ssid_prefix is None else ssid_prefix
    )

    if selected_delay < 0:
        raise ValueError("delay_seconds cannot be negative")

    for name, value in (
        ("wifi_iface", selected_wifi_iface),
        ("eth_iface", selected_eth_iface),
        ("ap_name", selected_ap_name),
        ("ssid_prefix", selected_ssid_prefix),
    ):
        if not value:
            raise ValueError(f"{name} cannot be empty")

    print(f"wifi-fallback: starting delay={selected_delay}s")

    if not nmcli_available():
        print("wifi-fallback: nmcli not available")
        return 1

    if selected_delay > 0:
        time.sleep(selected_delay)

    if ethernet_connected(selected_eth_iface):
        print("wifi-fallback: ethernet connected, exiting")
        return 0

    if not enable_wifi_radio(
        dry_run=dry_run,
    ):
        return 1

    if wait_for_wifi_ip(
        selected_wifi_iface,
        timeout_seconds=5,
    ):
        print("wifi-fallback: wifi has IP, exiting")
        return 0

    print("wifi-fallback: wifi has no IP, will start AP")

    if not ap_connection_exists(selected_ap_name):
        print(f"wifi-fallback: AP connection not found: {selected_ap_name}")
        return 1

    ssid = dynamic_ssid(selected_ssid_prefix)

    if not set_ap_ssid(
        selected_ap_name,
        ssid,
        dry_run=dry_run,
    ):
        return 1

    if not start_ap(
        selected_ap_name,
        dry_run=dry_run,
    ):
        return 1

    print("wifi-fallback: AP started")
    return 0


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG
    network = config.network

    parser = argparse.ArgumentParser(prog="betabox wifi-fallback")

    parser.add_argument(
        "--delay",
        type=int,
        default=(network.wifi_fallback_delay_seconds),
    )

    parser.add_argument(
        "--wifi-iface",
        default=network.wifi_interface,
    )

    parser.add_argument(
        "--eth-iface",
        default=network.ethernet_interface,
    )

    parser.add_argument(
        "--ap-name",
        default=network.ap_connection_name,
    )

    parser.add_argument(
        "--ssid-prefix",
        default=network.identity_prefix,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    args = parser.parse_args(argv)

    if args.delay < 0:
        print("--delay cannot be negative")
        return 1

    return run_wifi_fallback(
        delay_seconds=args.delay,
        wifi_iface=args.wifi_iface,
        eth_iface=args.eth_iface,
        ap_name=args.ap_name,
        ssid_prefix=args.ssid_prefix,
        dry_run=args.dry_run,
        config=config,
    )


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
