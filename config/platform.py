from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
class PlatformConfig:
    """
    Operational configuration shared by Betabox services, CLI tools,
    and future platform applications such as Launchpad.
    """

    paths: PlatformPathsConfig
    health: PlatformHealthConfig

    @classmethod
    def default(cls) -> "PlatformConfig":
        return cls(
            paths=PlatformPathsConfig.default(),
            health=PlatformHealthConfig(),
        )


DEFAULT_PLATFORM_CONFIG = PlatformConfig.default()
