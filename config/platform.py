from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TypeVar

EnumType = TypeVar(
    "EnumType",
    bound=Enum,
)


def _validate_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")

    return value


def _validate_int(
    value: object,
    *,
    name: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(f"{name} must be an integer")

    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")

    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")

    return value


def _validate_number(
    value: object,
    *,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError(f"{name} must be a number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")

    return number


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(value, str):
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
    if not isinstance(value, Path):
        raise TypeError(f"{name} must be a Path")

    return value.expanduser()


def _validate_enum(
    value: object,
    *,
    name: str,
    enum_type: type[EnumType],
) -> EnumType:
    if not isinstance(
        value,
        enum_type,
    ):
        raise TypeError(f"{name} must be a {enum_type.__name__}")

    return value


def _validate_string_tuple(
    value: object,
    *,
    name: str,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple of strings")

    normalized: list[str] = []

    for item in value:
        normalized.append(
            _validate_string(
                item,
                name=f"{name} item",
            )
        )

    return tuple(normalized)


class ServiceCategory(
    str,
    Enum,
):
    BOOT = "boot"
    BACKGROUND = "background"
    WEB = "web"
    NETWORK = "network"


class ServiceStartup(
    str,
    Enum,
):
    CONTINUOUS = "continuous"
    ONESHOT = "oneshot"
    CONDITIONAL = "conditional"


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformPathsConfig:
    """
    Filesystem locations used by the installed Betabox Platform.

    Child paths are derived from a small number of authoritative roots
    to prevent related directories from becoming inconsistent.
    """

    home: Path
    repository_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "home",
            _validate_path(
                self.home,
                name="home",
            ),
        )
        object.__setattr__(
            self,
            "repository_root",
            _validate_path(
                self.repository_root,
                name="repository_root",
            ),
        )

    @classmethod
    def default(
        cls,
    ) -> PlatformPathsConfig:
        return cls(
            home=Path.home(),
            repository_root=Path("/opt/libs/betabox_robotics"),
        )

    @property
    def media_root(self) -> Path:
        return self.home / "media"

    @property
    def pictures_dir(self) -> Path:
        return self.media_root / "pictures"

    @property
    def videos_dir(self) -> Path:
        return self.media_root / "videos"

    @property
    def sounds_dir(self) -> Path:
        return self.media_root / "sounds"

    @property
    def config_dir(self) -> Path:
        return self.home / ".config"

    @property
    def state_dir(self) -> Path:
        return self.home / ".local" / "state" / "betabox"

    @property
    def calibration_file(self) -> Path:
        return self.state_dir / "calibration.json"

    @property
    def events_file(self) -> Path:
        return self.state_dir / "events.jsonl"

    @property
    def monitor_log(self) -> Path:
        return self.state_dir / "monitor.log"

    @property
    def boot_announce_log(self) -> Path:
        return self.state_dir / "boot_announce.log"

    @property
    def video_log(self) -> Path:
        return self.state_dir / "video.log"

    @property
    def backup_root(self) -> Path:
        return self.home / "betabox-backups"

    @property
    def snapshot_root(self) -> Path:
        return self.home / "betabox-snapshots"

    @property
    def docs_dir(self) -> Path:
        return self.repository_root / "docs"

    @property
    def deployment_dir(self) -> Path:
        return self.repository_root / "deployment"

    @property
    def backup_sources(
        self,
    ) -> tuple[Path, ...]:
        return (
            self.media_root,
            self.config_dir,
            self.state_dir,
            self.docs_dir,
            self.deployment_dir,
        )

    @property
    def restore_paths(
        self,
    ) -> tuple[Path, ...]:
        return (
            self.media_root,
            self.config_dir,
            self.state_dir,
        )

    @property
    def reset_paths(
        self,
    ) -> tuple[Path, ...]:
        return (
            self.pictures_dir,
            self.videos_dir,
        )

    @property
    def recreate_paths(
        self,
    ) -> tuple[Path, ...]:
        return (
            self.pictures_dir,
            self.videos_dir,
            self.sounds_dir,
        )

    @property
    def car_honk_sound(self) -> Path:
        return self.sounds_dir / "car-honk.mp3"


@dataclass(
    frozen=True,
    slots=True,
)
class UsageThresholdConfig:
    high_percent: float = 85.0
    critical_percent: float = 95.0

    def __post_init__(self) -> None:
        high_percent = _validate_number(
            self.high_percent,
            name="high_percent",
        )
        critical_percent = _validate_number(
            self.critical_percent,
            name="critical_percent",
        )

        if not 0.0 <= high_percent <= 100.0:
            raise ValueError("high_percent must be between 0 and 100")

        if not 0.0 <= critical_percent <= 100.0:
            raise ValueError("critical_percent must be between 0 and 100")

        if high_percent >= critical_percent:
            raise ValueError("high_percent must be less than critical_percent")

        object.__setattr__(
            self,
            "high_percent",
            high_percent,
        )
        object.__setattr__(
            self,
            "critical_percent",
            critical_percent,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class TemperatureThresholdConfig:
    high_celsius: float = 75.0
    critical_celsius: float = 85.0

    def __post_init__(self) -> None:
        high_celsius = _validate_number(
            self.high_celsius,
            name="high_celsius",
        )
        critical_celsius = _validate_number(
            self.critical_celsius,
            name="critical_celsius",
        )

        if high_celsius >= critical_celsius:
            raise ValueError("high_celsius must be less than critical_celsius")

        object.__setattr__(
            self,
            "high_celsius",
            high_celsius,
        )
        object.__setattr__(
            self,
            "critical_celsius",
            critical_celsius,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class LaunchpadConfig:
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "enabled",
            _validate_bool(
                self.enabled,
                name="enabled",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformHealthConfig:
    temperature: TemperatureThresholdConfig = field(
        default_factory=TemperatureThresholdConfig
    )
    memory: UsageThresholdConfig = field(default_factory=UsageThresholdConfig)
    disk: UsageThresholdConfig = field(default_factory=UsageThresholdConfig)

    disk_path: Path = Path("/")
    ethernet_interface: str = "eth0"
    wifi_interface: str = "wlan0"

    def __post_init__(self) -> None:
        if not isinstance(
            self.temperature,
            TemperatureThresholdConfig,
        ):
            raise TypeError("temperature must be a TemperatureThresholdConfig")

        if not isinstance(
            self.memory,
            UsageThresholdConfig,
        ):
            raise TypeError("memory must be a UsageThresholdConfig")

        if not isinstance(
            self.disk,
            UsageThresholdConfig,
        ):
            raise TypeError("disk must be a UsageThresholdConfig")

        object.__setattr__(
            self,
            "disk_path",
            _validate_path(
                self.disk_path,
                name="disk_path",
            ),
        )
        object.__setattr__(
            self,
            "ethernet_interface",
            _validate_string(
                self.ethernet_interface,
                name="ethernet_interface",
            ),
        )
        object.__setattr__(
            self,
            "wifi_interface",
            _validate_string(
                self.wifi_interface,
                name="wifi_interface",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformNetworkConfig:
    """
    Network endpoints exposed by the installed Betabox Platform.
    """

    local_host: str = "127.0.0.1"
    bind_host: str = "0.0.0.0"

    jupyterhub_port: int = 8000
    vision_port: int = 8080
    launchpad_port: int = 8088

    wifi_interface: str = "wlan0"
    ethernet_interface: str = "eth0"
    ap_connection_name: str = "PiAP"
    identity_prefix: str = "Betabox"

    wifi_fallback_delay_seconds: int = 20

    def __post_init__(self) -> None:
        for name in (
            "local_host",
            "bind_host",
            "wifi_interface",
            "ethernet_interface",
            "ap_connection_name",
            "identity_prefix",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                ),
            )

        for name in (
            "jupyterhub_port",
            "vision_port",
            "launchpad_port",
        ):
            object.__setattr__(
                self,
                name,
                _validate_int(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                    minimum=1,
                    maximum=65535,
                ),
            )

        object.__setattr__(
            self,
            "wifi_fallback_delay_seconds",
            _validate_int(
                self.wifi_fallback_delay_seconds,
                name=("wifi_fallback_delay_seconds"),
                minimum=0,
            ),
        )

    @property
    def jupyterhub_url(self) -> str:
        return f"http://{self.local_host}:{self.jupyterhub_port}"

    @property
    def jupyterhub_health_url(self) -> str:
        return f"{self.jupyterhub_url}/hub/health"

    @property
    def vision_url(self) -> str:
        return f"http://{self.local_host}:{self.vision_port}"

    @property
    def launchpad_url(self) -> str:
        return f"http://{self.local_host}:{self.launchpad_port}"

    @property
    def launchpad_health_url(self) -> str:
        return f"{self.launchpad_url}/api/health"

    @property
    def launchpad_bind_address(
        self,
    ) -> tuple[str, int]:
        return (
            self.bind_host,
            self.launchpad_port,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ServiceDefinition:
    """
    Describes a systemd service exposed by the Betabox Platform.

    This metadata is safe for use by read-only interfaces such as the
    Launchpad Services page.
    """

    unit: str
    display_name: str
    description: str
    category: ServiceCategory
    startup: ServiceStartup

    def __post_init__(self) -> None:
        for name in (
            "unit",
            "display_name",
            "description",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                ),
            )

        object.__setattr__(
            self,
            "category",
            _validate_enum(
                self.category,
                name="category",
                enum_type=ServiceCategory,
            ),
        )
        object.__setattr__(
            self,
            "startup",
            _validate_enum(
                self.startup,
                name="startup",
                enum_type=ServiceStartup,
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformServicesConfig:
    """
    Systemd services used by the Betabox Platform.

    Each configured service includes its systemd unit name and
    read-only descriptive metadata for CLI and Launchpad interfaces.
    """

    hostname: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit=("set-hostname-from-serial.service"),
            display_name="Robot Hostname",
            description=(
                "Sets the robot hostname from its Raspberry Pi serial number."
            ),
            category=ServiceCategory.BOOT,
            startup=ServiceStartup.ONESHOT,
        )
    )

    boot_announce: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit=("betabox-boot-announce.service"),
            display_name="Boot Announcer",
            description=("Checks startup readiness and announces the robot's status."),
            category=ServiceCategory.BOOT,
            startup=ServiceStartup.ONESHOT,
        )
    )

    monitor: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit="betabox-monitor.service",
            display_name="Health Monitor",
            description=(
                "Continuously monitors platform health and records important events."
            ),
            category=ServiceCategory.BACKGROUND,
            startup=ServiceStartup.CONTINUOUS,
        )
    )

    jupyterhub: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit="jupyterhub.service",
            display_name="JupyterHub",
            description=(
                "Provides browser-based Python notebooks for robot programming."
            ),
            category=ServiceCategory.WEB,
            startup=ServiceStartup.CONTINUOUS,
        )
    )

    video: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit="betabox-video.service",
            display_name="Video Service",
            description=(
                "Runs the robot camera, streaming, snapshot, and recording services."
            ),
            category=ServiceCategory.BACKGROUND,
            startup=ServiceStartup.CONTINUOUS,
        )
    )

    wifi_fallback: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit="wifi-fallback.service",
            display_name="Wi-Fi Fallback",
            description=(
                "Starts the robot access point when "
                "no usable network connection exists."
            ),
            category=ServiceCategory.NETWORK,
            startup=ServiceStartup.CONDITIONAL,
        )
    )

    guest_reset: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit="betabox-guest-reset.service",
            display_name=("Guest Workspace Reset"),
            description=(
                "Resets and provisions the temporary "
                "Guest workspace during system startup."
            ),
            category=ServiceCategory.BOOT,
            startup=ServiceStartup.ONESHOT,
        )
    )

    launchpad: ServiceDefinition = field(
        default_factory=lambda: ServiceDefinition(
            unit="betabox-launchpad.service",
            display_name="Launchpad",
            description=(
                "Provides the local browser interface "
                "for robot tools and platform status."
            ),
            category=ServiceCategory.WEB,
            startup=ServiceStartup.CONTINUOUS,
        )
    )

    def __post_init__(self) -> None:
        for name in (
            "hostname",
            "boot_announce",
            "monitor",
            "jupyterhub",
            "video",
            "wifi_fallback",
            "guest_reset",
            "launchpad",
        ):
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                ServiceDefinition,
            ):
                raise TypeError(f"{name} must be a ServiceDefinition")

        units = self.all_units

        if len(set(units)) != len(units):
            raise ValueError("service unit names must be unique")

    @property
    def all_services(
        self,
    ) -> tuple[ServiceDefinition, ...]:
        return (
            self.hostname,
            self.boot_announce,
            self.monitor,
            self.jupyterhub,
            self.video,
            self.wifi_fallback,
            self.guest_reset,
            self.launchpad,
        )

    @property
    def all_units(
        self,
    ) -> tuple[str, ...]:
        return tuple(service.unit for service in self.all_services)

    def get(
        self,
        unit: str,
    ) -> ServiceDefinition | None:
        """
        Return metadata for a configured systemd unit.

        Returns ``None`` when the unit is not part of the Betabox
        service registry.
        """

        unit_value = _validate_string(
            unit,
            name="unit",
        )

        for service in self.all_services:
            if service.unit == unit_value:
                return service

        return None


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformVerificationConfig:
    """
    Requirements verified on an installed Betabox Platform.
    """

    i2c_device: Path = Path("/dev/i2c-1")
    i2c_bus: int = 1

    boot_config_file: Path = Path("/boot/firmware/config.txt")

    required_boot_config_lines: tuple[str, ...] = (
        "dtparam=i2c_arm=on",
        "dtparam=spi=on",
        "dtoverlay=hifiberry-dac",
        "dtoverlay=i2s-mmap",
    )

    required_python_modules: tuple[str, ...] = (
        "betabox_robotics",
        "cv2",
        "numpy",
        "pyaudio",
        "gpiozero",
        "smbus2",
        "aiohttp",
        "aiortc",
    )

    required_executables: tuple[str, ...] = (
        "node",
        "npm",
        "configurable-http-proxy",
    )

    hifiberry_identifiers: tuple[str, ...] = (
        "snd_rpi_hifiberry_dac",
        "HifiBerry",
    )

    command_timeout_seconds: int = 5

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "i2c_device",
            _validate_path(
                self.i2c_device,
                name="i2c_device",
            ),
        )
        object.__setattr__(
            self,
            "boot_config_file",
            _validate_path(
                self.boot_config_file,
                name="boot_config_file",
            ),
        )
        object.__setattr__(
            self,
            "i2c_bus",
            _validate_int(
                self.i2c_bus,
                name="i2c_bus",
                minimum=0,
            ),
        )
        object.__setattr__(
            self,
            "command_timeout_seconds",
            _validate_int(
                self.command_timeout_seconds,
                name=("command_timeout_seconds"),
                minimum=1,
            ),
        )

        for name in (
            "required_boot_config_lines",
            "required_python_modules",
            "required_executables",
            "hifiberry_identifiers",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(
                        self,
                        name,
                    ),
                    name=name,
                ),
            )


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformMonitoringConfig:
    """
    Defaults used by platform monitoring, events, and log tools.
    """

    interval_seconds: int = 60
    default_event_count: int = 20
    default_log_lines: int = 50

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "interval_seconds",
            _validate_int(
                self.interval_seconds,
                name="interval_seconds",
                minimum=1,
            ),
        )
        object.__setattr__(
            self,
            "default_event_count",
            _validate_int(
                self.default_event_count,
                name="default_event_count",
                minimum=0,
            ),
        )
        object.__setattr__(
            self,
            "default_log_lines",
            _validate_int(
                self.default_log_lines,
                name="default_log_lines",
                minimum=1,
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformRuntimeConfig:
    """
    Runtime defaults for installed Betabox services.
    """

    vision_fps: int = 20

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "vision_fps",
            _validate_int(
                self.vision_fps,
                name="vision_fps",
                minimum=1,
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PlatformConfig:
    """
    Operational configuration shared by Betabox services, CLI tools,
    and platform applications such as Launchpad.
    """

    paths: PlatformPathsConfig
    health: PlatformHealthConfig
    network: PlatformNetworkConfig
    services: PlatformServicesConfig
    verification: PlatformVerificationConfig
    monitoring: PlatformMonitoringConfig
    runtime: PlatformRuntimeConfig
    launchpad: LaunchpadConfig

    def __post_init__(self) -> None:
        expected_types = (
            (
                "paths",
                PlatformPathsConfig,
            ),
            (
                "health",
                PlatformHealthConfig,
            ),
            (
                "network",
                PlatformNetworkConfig,
            ),
            (
                "services",
                PlatformServicesConfig,
            ),
            (
                "verification",
                PlatformVerificationConfig,
            ),
            (
                "monitoring",
                PlatformMonitoringConfig,
            ),
            (
                "runtime",
                PlatformRuntimeConfig,
            ),
            (
                "launchpad",
                LaunchpadConfig,
            ),
        )

        for name, expected_type in expected_types:
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                expected_type,
            ):
                raise TypeError(f"{name} must be a {expected_type.__name__}")

    @classmethod
    def default(
        cls,
    ) -> PlatformConfig:
        return cls(
            paths=PlatformPathsConfig.default(),
            health=PlatformHealthConfig(),
            network=PlatformNetworkConfig(),
            services=PlatformServicesConfig(),
            verification=(PlatformVerificationConfig()),
            monitoring=PlatformMonitoringConfig(),
            runtime=PlatformRuntimeConfig(),
            launchpad=LaunchpadConfig(),
        )


DEFAULT_PLATFORM_CONFIG = PlatformConfig.default()
