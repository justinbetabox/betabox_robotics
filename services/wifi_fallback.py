from __future__ import annotations

import argparse
import time
from subprocess import CompletedProcess
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run
from betabox_robotics.services.identity import (
    identity_name,
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


def _validate_non_negative_int(
    value: object,
    *,
    name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer")

    if value < 0:
        raise ValueError(f"{name} cannot be negative")

    return value


def _validate_positive_float(
    value: object,
    *,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError(f"{name} must be a number")

    result = float(value)

    if result <= 0:
        raise ValueError(f"{name} must be greater than 0")

    return result


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


def wait_for_wifi_ip(
    iface: str,
    *,
    timeout_seconds: int = 5,
    poll_interval: float = 0.5,
) -> bool:
    iface_value = _validate_string(
        iface,
        name="iface",
    )
    timeout_value = _validate_non_negative_int(
        timeout_seconds,
        name="timeout_seconds",
    )
    poll_value = _validate_positive_float(
        poll_interval,
        name="poll_interval",
    )

    deadline = time.monotonic() + timeout_value

    while time.monotonic() < deadline:
        if wifi_has_ip(iface_value):
            return True

        time.sleep(poll_value)

    return wifi_has_ip(iface_value)


def dynamic_ssid(
    prefix: str,
) -> str:
    prefix_value = _validate_string(
        prefix,
        name="prefix",
    )

    name = identity_name(
        prefix_value,
        fallback="UNKNOWN",
    )

    if name is None:
        raise RuntimeError("failed to construct fallback SSID")

    return _validate_string(
        name,
        name="ssid",
    )


def nmcli_available() -> bool:
    result = run(
        [
            "which",
            "nmcli",
        ],
        timeout=3,
    )

    return bool(result is not None and result.returncode == 0)


def command_error(
    result: CompletedProcess[str] | None,
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
        result is not None
        and result.returncode == 0
        and result.stdout.strip() == "enabled"
    )


def enable_wifi_radio(
    *,
    dry_run: bool = False,
) -> bool:
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )
    if wifi_radio_enabled():
        return True

    print("wifi-fallback: Wi-Fi radio is disabled, enabling it")

    if dry_run_value:
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
            + f"Wi-Fi radio: {command_error(enable_result)}"
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
    iface_value = _validate_string(
        iface,
        name="iface",
    )

    result = run(
        [
            "nmcli",
            "-g",
            "GENERAL.STATE",
            "device",
            "show",
            iface_value,
        ],
        timeout=5,
    )

    if result is None or result.returncode != 0:
        return False

    return result.stdout.strip().startswith("100")


def wifi_has_ip(
    iface: str,
) -> bool:
    iface_value = _validate_string(
        iface,
        name="iface",
    )

    result = run(
        [
            "nmcli",
            "-g",
            "IP4.ADDRESS",
            "device",
            "show",
            iface_value,
        ],
        timeout=5,
    )

    if result is None or result.returncode != 0:
        return False

    return bool(result.stdout.strip())


def ap_connection_exists(
    ap_name: str,
) -> bool:
    ap_name_value = _validate_string(
        ap_name,
        name="ap_name",
    )

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

    if result is None or result.returncode != 0:
        return False

    names = {line.strip() for line in result.stdout.splitlines() if line.strip()}

    return ap_name_value in names


def set_ap_ssid(
    ap_name: str,
    ssid: str,
    *,
    dry_run: bool = False,
) -> bool:
    ap_name_value = _validate_string(
        ap_name,
        name="ap_name",
    )
    ssid_value = _validate_string(
        ssid,
        name="ssid",
    )
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )

    print(f"wifi-fallback: using SSID: {ssid_value}")

    if dry_run_value:
        print(f"wifi-fallback: would set {ap_name_value} SSID to {ssid_value}")
        return True

    result = run(
        [
            "nmcli",
            "connection",
            "modify",
            ap_name_value,
            "802-11-wireless.ssid",
            ssid_value,
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
    ap_name_value = _validate_string(
        ap_name,
        name="ap_name",
    )
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )

    print(f"wifi-fallback: bringing up AP connection: {ap_name_value}")

    if dry_run_value:
        print(f"wifi-fallback: would run nmcli connection up {ap_name_value}")
        return True

    result = run(
        [
            "nmcli",
            "connection",
            "up",
            ap_name_value,
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
    config_value = _validate_config(config)
    dry_run_value = _validate_flag(
        dry_run,
        name="dry_run",
    )
    network = config_value.network

    selected_delay = (
        network.wifi_fallback_delay_seconds if delay_seconds is None else delay_seconds
    )
    delay_value = _validate_non_negative_int(
        selected_delay,
        name="delay_seconds",
    )

    wifi_iface_value = _validate_string(
        (network.wifi_interface if wifi_iface is None else wifi_iface),
        name="wifi_iface",
    )
    eth_iface_value = _validate_string(
        (network.ethernet_interface if eth_iface is None else eth_iface),
        name="eth_iface",
    )
    ap_name_value = _validate_string(
        (network.ap_connection_name if ap_name is None else ap_name),
        name="ap_name",
    )
    ssid_prefix_value = _validate_string(
        (network.identity_prefix if ssid_prefix is None else ssid_prefix),
        name="ssid_prefix",
    )
    print(f"wifi-fallback: starting delay={delay_value}s")

    if not nmcli_available():
        print("wifi-fallback: nmcli not available")
        return 1

    if delay_value > 0:
        if dry_run_value:
            print(f"wifi-fallback: would wait {delay_value}s")
        else:
            time.sleep(delay_value)

    if ethernet_connected(eth_iface_value):
        print("wifi-fallback: ethernet connected, exiting")
        return 0

    if not enable_wifi_radio(
        dry_run=dry_run_value,
    ):
        return 1

    if wait_for_wifi_ip(
        wifi_iface_value,
        timeout_seconds=5,
    ):
        print("wifi-fallback: wifi has IP, exiting")
        return 0

    print("wifi-fallback: wifi has no IP, will start AP")

    if not ap_connection_exists(ap_name_value):
        print(f"wifi-fallback: AP connection not found: {ap_name_value}")
        return 1

    ssid = dynamic_ssid(ssid_prefix_value)

    if not set_ap_ssid(
        ap_name_value,
        ssid,
        dry_run=dry_run_value,
    ):
        return 1

    if not start_ap(
        ap_name_value,
        dry_run=dry_run_value,
    ):
        return 1

    print("wifi-fallback: AP started")
    return 0


def parse_args(
    argv: list[str] | None = None,
    *,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> argparse.Namespace:
    config_value = _validate_config(config)
    network = config_value.network

    parser = argparse.ArgumentParser(prog="betabox wifi-fallback")

    _ = parser.add_argument(
        "--delay",
        type=int,
        default=(network.wifi_fallback_delay_seconds),
    )
    _ = parser.add_argument(
        "--wifi-iface",
        default=network.wifi_interface,
    )
    _ = parser.add_argument(
        "--eth-iface",
        default=network.ethernet_interface,
    )
    _ = parser.add_argument(
        "--ap-name",
        default=network.ap_connection_name,
    )
    _ = parser.add_argument(
        "--ssid-prefix",
        default=network.identity_prefix,
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
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
        delay_seconds = _validate_non_negative_int(
            cast(
                object,
                args.delay,
            ),
            name="delay_seconds",
        )

        wifi_iface = _validate_string(
            cast(
                object,
                args.wifi_iface,
            ),
            name="wifi_iface",
        )

        eth_iface = _validate_string(
            cast(
                object,
                args.eth_iface,
            ),
            name="eth_iface",
        )

        ap_name = _validate_string(
            cast(
                object,
                args.ap_name,
            ),
            name="ap_name",
        )

        ssid_prefix = _validate_string(
            cast(
                object,
                args.ssid_prefix,
            ),
            name="ssid_prefix",
        )

        dry_run = _validate_flag(
            cast(
                object,
                args.dry_run,
            ),
            name="dry_run",
        )

        return run_wifi_fallback(
            delay_seconds=delay_seconds,
            wifi_iface=wifi_iface,
            eth_iface=eth_iface,
            ap_name=ap_name,
            ssid_prefix=ssid_prefix,
            dry_run=dry_run,
            config=config,
        )

    except (
        TypeError,
        ValueError,
        OSError,
        RuntimeError,
    ) as exc:
        print(f"wifi-fallback: {exc}")
        return 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
