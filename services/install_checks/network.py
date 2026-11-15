from __future__ import annotations

from pathlib import Path

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.command import run

from .models import CheckResult
from .validation import validate_config

NGINX_AVAILABLE = Path("/etc/nginx/sites-available/betabox")
NGINX_ENABLED = Path("/etc/nginx/sites-enabled/betabox")
DNS_CONFIG = Path("/etc/NetworkManager/dnsmasq-shared.d/betabox.conf")


def check_nginx_site() -> CheckResult:
    name = "network:nginx-site"

    if not NGINX_AVAILABLE.is_file():
        return CheckResult(name, False, f"Missing {NGINX_AVAILABLE}")

    if not NGINX_ENABLED.is_symlink():
        return CheckResult(name, False, f"Missing site symlink: {NGINX_ENABLED}")

    if NGINX_ENABLED.resolve() != NGINX_AVAILABLE:
        return CheckResult(name, False, "Nginx site symlink points to wrong file")

    return CheckResult(name, True, "Betabox Nginx site installed and enabled")


def check_offline_dns(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    config_value = validate_config(config)
    name = "network:offline-dns"

    if not DNS_CONFIG.is_file():
        return CheckResult(name, False, f"Missing {DNS_CONFIG}")

    try:
        lines = DNS_CONFIG.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return CheckResult(name, False, str(exc))

    expected = (
        f"address=/{config_value.network.offline_hostname}/"
        f"{config_value.network.ap_ipv4_address}"
    )

    present = expected in (line.strip() for line in lines)

    return CheckResult(
        name,
        present,
        "Offline DNS mapping configured" if present else f"Missing {expected}",
    )


def check_ap_profile(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> CheckResult:
    config_value = validate_config(config)
    network = config_value.network
    name = "network:ap-profile"

    properties = (
        "connection.interface-name",
        "connection.autoconnect",
        "802-11-wireless.mode",
        "802-11-wireless-security.key-mgmt",
        "ipv4.method",
        "ipv4.addresses",
        "ipv6.method",
    )

    values: dict[str, str] = {}

    for property_name in properties:
        result = run(
            [
                "nmcli",
                "-g",
                property_name,
                "connection",
                "show",
                network.ap_connection_name,
            ],
            timeout=config_value.verification.command_timeout_seconds,
        )

        if result is None or result.returncode != 0:
            return CheckResult(
                name,
                False,
                f"Unable to read {property_name}",
            )

        values[property_name] = result.stdout.strip()

    problems: list[str] = []

    if values["connection.interface-name"] != network.wifi_interface:
        problems.append("Incorrect Wi-Fi interface")

    if values["connection.autoconnect"] != "no":
        problems.append("AP autoconnect should be disabled")

    if values["802-11-wireless.mode"] != "ap":
        problems.append("Wi-Fi mode is not AP")

    if values["802-11-wireless-security.key-mgmt"] not in ("", "--"):
        problems.append("Wi-Fi security is not open")

    if values["ipv4.method"] != "shared":
        problems.append("IPv4 method is not shared")

    expected_address = f"{network.ap_ipv4_address}/24"

    configured_addresses = {
        address.strip()
        for address in values["ipv4.addresses"].split(",")
        if address.strip()
    }

    if expected_address not in configured_addresses:
        problems.append(f"Expected {expected_address}")

    if values["ipv6.method"] != "ignore":
        problems.append("IPv6 method is not ignore")

    return CheckResult(
        name,
        not problems,
        "; ".join(problems) if problems else "Open AP profile configured",
    )
