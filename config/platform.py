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


@dataclass(frozen=True)
class PlatformConfig:
    """
    Operational configuration shared by Betabox services, CLI tools,
    and future platform applications such as Launchpad.
    """

    paths: PlatformPathsConfig

    @classmethod
    def default(cls) -> "PlatformConfig":
        return cls(
            paths=PlatformPathsConfig.default(),
        )


DEFAULT_PLATFORM_CONFIG = PlatformConfig.default()
