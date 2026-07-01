import socket
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaPaths:
    pictures: Path
    videos: Path


@dataclass(frozen=True)
class SystemStatus:
    hostname: str
    ip_addresses: list[str]
    media: MediaPaths


class System:
    """
    System information and platform paths.
    """

    def hostname(self) -> str:
        return socket.gethostname()

    def ip_addresses(self) -> list[str]:
        addresses: list[str] = []

        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                address = info[4][0]

                if address not in addresses and not address.startswith("127."):
                    addresses.append(address)

        except socket.gaierror:
            pass

        return addresses

    def media_paths(self) -> MediaPaths:
        base = Path.home() / "media"

        return MediaPaths(
            pictures=base / "pictures",
            videos=base / "videos",
        )

    def ensure_media_paths(self) -> MediaPaths:
        paths = self.media_paths()

        paths.pictures.mkdir(parents=True, exist_ok=True)
        paths.videos.mkdir(parents=True, exist_ok=True)

        return paths

    def status(self) -> SystemStatus:
        return SystemStatus(
            hostname=self.hostname(),
            ip_addresses=self.ip_addresses(),
            media=self.media_paths(),
        )

    def stop_all(self) -> None:
        """
        Placeholder for future coordinated shutdown behavior.
        """
        return None
