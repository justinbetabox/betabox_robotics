from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from enum import Enum


class ServiceCategory(str, Enum):
    BOOT = "boot"
    BACKGROUND = "background"
    WEB = "web"
    NETWORK = "network"


class ServiceStartup(str, Enum):
    CONTINUOUS = "continuous"
    ONESHOT = "oneshot"
    CONDITIONAL = "conditional"

@dataclass(frozen=True)
class PlatformPathsConfig:
    """
    Filesystem locations used by the installed Betabox Platform.

    Child paths are derived from a small number of authoritative roots
    to prevent related directories from becoming inconsistent.
    """

    home: Path
    repository_root: Path

    @classmethod
    def default(cls) -> "PlatformPathsConfig":
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
    def backup_sources(self) -> tuple[Path, ...]:
        return (
            self.media_root,
            self.config_dir,
            self.state_dir,
            self.docs_dir,
            self.deployment_dir,
        )

    @property
    def restore_paths(self) -> tuple[Path, ...]:
        return (
            self.media_root,
            self.config_dir,
            self.state_dir,
        )

    @property
    def reset_paths(self) -> tuple[Path, ...]:
        return (
            self.pictures_dir,
            self.videos_dir,
        )

    @property
    def recreate_paths(self) -> tuple[Path, ...]:
        return (
            self.pictures_dir,
            self.videos_dir,
            self.sounds_dir,
        )

    @property
    def car_honk_sound(self) -> Path:
        return self.sounds_dir / "car-honk.mp3"

@dataclass(frozen=True)
class UsageThresholdConfig:
    high_percent: float = 85.0
    critical_percent: float = 95.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.high_percent <= 100.0:
            raise ValueError(
                "high_percent must be between 0 and 100"
            )

        if not 0.0 <= self.critical_percent <= 100.0:
            raise ValueError(
                "critical_percent must be between 0 and 100"
            )

        if self.high_percent >= self.critical_percent:
            raise ValueError(
                "high_percent must be less than critical_percent"
            )


@dataclass(frozen=True)
class TemperatureThresholdConfig:
    high_celsius: float = 75.0
    critical_celsius: float = 85.0

    def __post_init__(self) -> None:
        if self.high_celsius >= self.critical_celsius:
            raise ValueError(
                "high_celsius must be less than critical_celsius"
            )

@dataclass(frozen=True)
class LaunchpadConfig:
    enabled: bool = True


@dataclass(frozen=True)
class PlatformHealthConfig:
    temperature: TemperatureThresholdConfig = (
        TemperatureThresholdConfig()
    )
    memory: UsageThresholdConfig = UsageThresholdConfig()
    disk: UsageThresholdConfig = UsageThresholdConfig()

    disk_path: Path = Path("/")
    ethernet_interface: str = "eth0"
    wifi_interface: str = "wlan0"

    def __post_init__(self) -> None:
        if not self.ethernet_interface:
            raise ValueError(
                "ethernet_interface cannot be empty"
            )

        if not self.wifi_interface:
            raise ValueError(
                "wifi_interface cannot be empty"
            )

@dataclass(frozen=True)
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
        if not self.local_host:
            raise ValueError("local_host cannot be empty")

        if not self.bind_host:
            raise ValueError("bind_host cannot be empty")

        for name, port in (
            ("jupyterhub_port", self.jupyterhub_port),
            ("vision_port", self.vision_port),
            ("launchpad_port", self.launchpad_port),
        ):
            if not 1 <= port <= 65535:
                raise ValueError(
                    f"{name} must be between 1 and 65535"
                )

        for name, value in (
            ("wifi_interface", self.wifi_interface),
            ("ethernet_interface", self.ethernet_interface),
            ("ap_connection_name", self.ap_connection_name),
            ("identity_prefix", self.identity_prefix),
        ):
            if not value:
                raise ValueError(
                    f"{name} cannot be empty"
                )

        if self.wifi_fallback_delay_seconds < 0:
            raise ValueError(
                "wifi_fallback_delay_seconds cannot be negative"
            )

    @property
    def jupyterhub_url(self) -> str:
        return (
            f"http://{self.local_host}:"
            f"{self.jupyterhub_port}"
        )

    @property
    def jupyterhub_health_url(self) -> str:
        return f"{self.jupyterhub_url}/hub/health"

    @property
    def vision_url(self) -> str:
        return (
            f"http://{self.local_host}:"
            f"{self.vision_port}"
        )

    @property
    def launchpad_url(self) -> str:
        return (
            f"http://{self.local_host}:"
            f"{self.launchpad_port}"
        )

    @property
    def launchpad_health_url(self) -> str:
        return (
            f"{self.launchpad_url}/api/health"
        )

    @property
    def launchpad_bind_address(self) -> tuple[str, int]:
        return (
            self.bind_host,
            self.launchpad_port,
        )

@dataclass(frozen=True)
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
        for name, value in (
            ("unit", self.unit),
            ("display_name", self.display_name),
            ("description", self.description),
        ):
            if not value:
                raise ValueError(
                    f"{name} cannot be empty"
                )


@dataclass(frozen=True)
class PlatformServicesConfig:
    """
    Systemd services used by the Betabox Platform.

    Each configured service includes its systemd unit name and
    read-only descriptive metadata for CLI and Launchpad interfaces.
    """

    hostname: ServiceDefinition = ServiceDefinition(
        unit="set-hostname-from-serial.service",
        display_name="Robot Hostname",
        description=(
            "Sets the robot hostname from "
            "its Raspberry Pi serial number."
        ),
        category=ServiceCategory.BOOT,
        startup=ServiceStartup.ONESHOT,
    )

    boot_announce: ServiceDefinition = ServiceDefinition(
        unit="betabox-boot-announce.service",
        display_name="Boot Announcer",
        description=(
            "Checks startup readiness and "
            "announces the robot's status."
        ),
        category=ServiceCategory.BOOT,
        startup=ServiceStartup.ONESHOT,
    )

    monitor: ServiceDefinition = ServiceDefinition(
        unit="betabox-monitor.service",
        display_name="Health Monitor",
        description=(
            "Continuously monitors platform "
            "health and records important events."
        ),
        category=ServiceCategory.BACKGROUND,
        startup=ServiceStartup.CONTINUOUS,
    )

    jupyterhub: ServiceDefinition = ServiceDefinition(
        unit="jupyterhub.service",
        display_name="JupyterHub",
        description=(
            "Provides browser-based Python "
            "notebooks for robot programming."
        ),
        category=ServiceCategory.WEB,
        startup=ServiceStartup.CONTINUOUS,
    )

    video: ServiceDefinition = ServiceDefinition(
        unit="betabox-video.service",
        display_name="Video Service",
        description=(
            "Runs the robot camera, streaming, "
            "snapshot, and recording services."
        ),
        category=ServiceCategory.BACKGROUND,
        startup=ServiceStartup.CONTINUOUS,
    )

    wifi_fallback: ServiceDefinition = ServiceDefinition(
        unit="wifi-fallback.service",
        display_name="Wi-Fi Fallback",
        description=(
            "Starts the robot access point when "
            "no usable network connection exists."
        ),
        category=ServiceCategory.NETWORK,
        startup=ServiceStartup.CONDITIONAL,
    )

    launchpad: ServiceDefinition = ServiceDefinition(
        unit="betabox-launchpad.service",
        display_name="Launchpad",
        description=(
            "Provides the local browser interface "
            "for robot tools and platform status."
        ),
        category=ServiceCategory.WEB,
        startup=ServiceStartup.CONTINUOUS,
    )

    def __post_init__(self) -> None:
        units = self.all_units

        if len(set(units)) != len(units):
            raise ValueError(
                "service unit names must be unique"
            )

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
            self.launchpad,
        )

    @property
    def all_units(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            service.unit
            for service in self.all_services
        )

    def get(
        self,
        unit: str,
    ) -> ServiceDefinition | None:
        """
        Return metadata for a configured systemd unit.

        Returns ``None`` when the unit is not part of the Betabox
        service registry.
        """

        for service in self.all_services:
            if service.unit == unit:
                return service

        return None


@dataclass(frozen=True)
class PlatformVerificationConfig:
    """
    Requirements verified on an installed Betabox Platform.
    """

    i2c_device: Path = Path("/dev/i2c-1")
    i2c_bus: int = 1

    boot_config_file: Path = Path(
        "/boot/firmware/config.txt"
    )

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
        if self.i2c_bus < 0:
            raise ValueError(
                "i2c_bus must be zero or greater"
            )

        if self.command_timeout_seconds <= 0:
            raise ValueError(
                "command_timeout_seconds must be greater than 0"
            )


@dataclass(frozen=True)
class PlatformMonitoringConfig:
    """
    Defaults used by platform monitoring, events, and log tools.
    """

    interval_seconds: int = 60
    default_event_count: int = 20
    default_log_lines: int = 50

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be greater than 0"
            )

        if self.default_event_count < 0:
            raise ValueError(
                "default_event_count cannot be negative"
            )

        if self.default_log_lines <= 0:
            raise ValueError(
                "default_log_lines must be greater than 0"
            )

@dataclass(frozen=True)
class PlatformRuntimeConfig:
    """
    Runtime defaults for installed Betabox services.
    """

    vision_fps: int = 20

    def __post_init__(self) -> None:
        if self.vision_fps <= 0:
            raise ValueError(
                "vision_fps must be greater than 0"
            )

@dataclass(frozen=True)
class PlatformConfig:
    """
    Operational configuration shared by Betabox services, CLI tools,
    and future platform applications such as Launchpad.
    """

    paths: PlatformPathsConfig
    health: PlatformHealthConfig
    network: PlatformNetworkConfig
    services: PlatformServicesConfig
    verification: PlatformVerificationConfig
    monitoring: PlatformMonitoringConfig
    runtime: PlatformRuntimeConfig
    launchpad: LaunchpadConfig

    @classmethod
    def default(cls) -> "PlatformConfig":
        return cls(
            paths=PlatformPathsConfig.default(),
            health=PlatformHealthConfig(),
            network=PlatformNetworkConfig(),
            services=PlatformServicesConfig(),
            verification=PlatformVerificationConfig(),
            monitoring=PlatformMonitoringConfig(),
            runtime=PlatformRuntimeConfig(),
            launchpad=LaunchpadConfig(),
        )


DEFAULT_PLATFORM_CONFIG = PlatformConfig.default()
