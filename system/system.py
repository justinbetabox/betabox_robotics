import socket
from dataclasses import dataclass
from pathlib import Path

from betabox_robotics.version import __version__


@dataclass(frozen=True)
class MediaPaths:
    pictures: Path
    videos: Path
    sounds: Path


@dataclass(frozen=True)
class SystemStatus:
    version: str
    hostname: str
    ip_addresses: list[str]
    media: MediaPaths


@dataclass(frozen=True)
class SystemHealth:
    ok: bool
    messages: list[str]


class System:
    """
    System information and platform paths.
    """

    @classmethod
    def default(cls, robot_config=None) -> "System":
        return cls()

    def hostname(self) -> str:
        return socket.gethostname()

    def ip_addresses(self) -> list[str]:
        addresses: list[str] = []

        try:
            hostname = socket.gethostname()

            for info in socket.getaddrinfo(hostname, None):
                address = info[4][0]

                if not isinstance(address, str):
                    continue

                if address.startswith("127."):
                    continue

                if address not in addresses:
                    addresses.append(address)

        except socket.gaierror:
            pass

        return addresses

    def media_paths(self) -> MediaPaths:
        base = Path.home() / "media"

        return MediaPaths(
            pictures=base / "pictures",
            videos=base / "videos",
            sounds=base / "sounds",
        )

    def ensure_media_paths(self) -> MediaPaths:
        paths = self.media_paths()

        paths.pictures.mkdir(parents=True, exist_ok=True)
        paths.videos.mkdir(parents=True, exist_ok=True)
        paths.sounds.mkdir(parents=True, exist_ok=True)

        return paths

    def status(self) -> SystemStatus:
        return SystemStatus(
            version=__version__,
            hostname=self.hostname(),
            ip_addresses=self.ip_addresses(),
            media=self.media_paths(),
        )

    def stop_all(self) -> None:
        """
        Placeholder for future coordinated shutdown behavior.
        """
        return None

    def health(self) -> SystemHealth:
        messages: list[str] = []

        media = self.media_paths()

        if not media.pictures.exists():
            messages.append(f"missing pictures directory: {media.pictures}")

        if not media.videos.exists():
            messages.append(f"missing videos directory: {media.videos}")

        if not media.sounds.exists():
            messages.append(f"missing sounds directory: {media.sounds}")

        return SystemHealth(
            ok=len(messages) == 0,
            messages=messages,
        )
