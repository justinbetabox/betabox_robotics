from __future__ import annotations

import json

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.system_checks import (
    SystemHealthStatus,
    collect_disk_status,
    collect_memory_status,
    collect_network_interface,
    collect_temperature_status,
    collect_throttling_status,
)
from betabox_robotics.services.system_checks.validation import (
    validate_config,
)


def collect_system_health(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> SystemHealthStatus:
    config_value = validate_config(config)

    return SystemHealthStatus(
        temperature=collect_temperature_status(config_value),
        throttling=collect_throttling_status(),
        memory=collect_memory_status(config_value),
        disk=collect_disk_status(config=config_value),
        ethernet=collect_network_interface(config_value.health.ethernet_interface),
        wifi=collect_network_interface(config_value.health.wifi_interface),
    )


def main() -> int:
    status = collect_system_health(DEFAULT_PLATFORM_CONFIG)

    print(
        json.dumps(
            status.to_dict(),
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
