import socket
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Self

from betabox_robotics.version import __version__


@dataclass(frozen=True)
class MediaPaths:
    pictures: Path
    videos: Path
    sounds: Path

    @property
    def all(self) -> tuple[Path, Path, Path]:
        return (
            self.pictures,
            self.videos,
            self.sounds,
        )

    def exists(self) -> bool:
        return all(path.exists() for path in self.all)

    def to_dict(self) -> dict[str, str]:
        return {
            "pictures": str(self.pictures),
            "videos": str(self.videos),
            "sounds": str(self.sounds),
        }


@dataclass(frozen=True)
class SystemStatus:
    version: str
    hostname: str
    ip_addresses: list[str]
    media: MediaPaths

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "hostname": self.hostname,
            "ip_addresses": list(self.ip_addresses),
            "media": self.media.to_dict(),
        }


@dataclass(frozen=True)
class SystemHealth:
    ok: bool
    messages: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SystemError(Exception):
    """Raised when System subsystem operations fail."""


class System:
    """
    System information and platform paths.
    """

    def __init__(self) -> None:
            self._closed = False

    def __enter__(self) -> Self:
        self._require_open()
        return self


    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise SystemError("system subsystem is closed")

    @classmethod
    def default(cls, robot_config: object | None = None) -> "System":
        return cls()

    def hostname(self) -> str:
        self._require_open()
        return socket.gethostname()

    def ip_addresses(self) -> list[str]:
        self._require_open()

        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except Exception:
            return []

        if result.returncode != 0:
            return []

        addresses: list[str] = []

        for address in result.stdout.split():
            if address.startswith("127."):
                continue

            if address not in addresses:
                addresses.append(address)

        return addresses

    def media_paths(self) -> MediaPaths:
        self._require_open()
        base = Path.home() / "media"

        return MediaPaths(
            pictures=base / "pictures",
            videos=base / "videos",
            sounds=base / "sounds",
        )

    def ensure_media_paths(self) -> MediaPaths:
        self._require_open()
        paths = self.media_paths()

        paths.pictures.mkdir(parents=True, exist_ok=True)
        paths.videos.mkdir(parents=True, exist_ok=True)
        paths.sounds.mkdir(parents=True, exist_ok=True)

        return paths

    def status(self) -> SystemStatus:
        self._require_open()
        return SystemStatus(
            version=__version__,
            hostname=self.hostname(),
            ip_addresses=self.ip_addresses(),
            media=self.media_paths(),
        )

    def stop_all(self) -> None:
        """
        Stop active System-managed behavior without closing the subsystem.

        System currently owns no active background behavior.
        """
        self._require_open()

    def health(self) -> SystemHealth:
        self._require_open()

        media = self.media_paths()

        messages = [
            f"missing media directory: {path}"
            for path in media.all
            if not path.exists()
        ]

        return SystemHealth(
            ok=not messages,
            messages=messages,
        )

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True


    def deinit(self) -> None:
        self.close()
