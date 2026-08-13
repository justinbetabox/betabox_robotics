from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Self, TypedDict

from betabox_robotics.version import __version__

if TYPE_CHECKING:
    from betabox_robotics.robots.config import SystemConfig


class SystemStatusDict(TypedDict):
    version: str
    hostname: str
    ip_addresses: list[str]
    media: dict[str, str]


class SystemHealthDict(TypedDict):
    ok: bool
    messages: list[str]


def _validate_path(
    value: object,
    *,
    name: str,
) -> Path:
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string or Path")

    return Path(value).expanduser()


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


@dataclass(frozen=True, slots=True)
class MediaPaths:
    pictures: Path
    videos: Path
    sounds: Path

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pictures",
            _validate_path(
                self.pictures,
                name="pictures",
            ),
        )
        object.__setattr__(
            self,
            "videos",
            _validate_path(
                self.videos,
                name="videos",
            ),
        )
        object.__setattr__(
            self,
            "sounds",
            _validate_path(
                self.sounds,
                name="sounds",
            ),
        )

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


@dataclass(frozen=True, slots=True)
class SystemStatus:
    version: str
    hostname: str
    ip_addresses: tuple[str, ...]
    media: MediaPaths

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "version",
            _validate_string(
                self.version,
                name="version",
            ),
        )
        object.__setattr__(
            self,
            "hostname",
            _validate_string(
                self.hostname,
                name="hostname",
            ),
        )

        object.__setattr__(
            self,
            "ip_addresses",
            tuple(
                _validate_string(
                    address,
                    name="IP address",
                )
                for address in self.ip_addresses
            ),
        )

    def to_dict(self) -> SystemStatusDict:
        return {
            "version": self.version,
            "hostname": self.hostname,
            "ip_addresses": list(self.ip_addresses),
            "media": self.media.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SystemHealth:
    ok: bool
    messages: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "messages",
            tuple(
                _validate_string(
                    message,
                    name="health message",
                )
                for message in self.messages
            ),
        )

    def to_dict(self) -> SystemHealthDict:
        return {
            "ok": self.ok,
            "messages": list(self.messages),
        }


class SystemError(Exception):
    """Raised when System subsystem operations fail."""


class System:
    """
    System information and platform paths.
    """

    _media_root: Path
    _closed: bool

    def __init__(
        self,
        *,
        media_root: str | Path | None = None,
    ) -> None:
        self._media_root = (
            Path.home() / "media"
            if media_root is None
            else _validate_path(
                media_root,
                name="media_root",
            )
        )
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
    def default(
        cls,
        config: SystemConfig,
    ) -> Self:
        return cls(
            media_root=config.media_root,
        )

    def hostname(self) -> str:
        self._require_open()

        try:
            hostname = socket.gethostname()
        except OSError as exc:
            raise SystemError(f"failed to read hostname: {exc}") from exc

        try:
            return _validate_string(
                hostname,
                name="hostname",
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise SystemError("system returned an invalid hostname") from exc

    def ip_addresses(self) -> tuple[str, ...]:
        self._require_open()

        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return ()

        if result.returncode != 0:
            return ()

        addresses: list[str] = []

        for address in result.stdout.split():
            normalized = address.strip()

            if (
                not normalized
                or normalized.startswith("127.")
                or normalized in addresses
            ):
                continue

            addresses.append(normalized)

        return tuple(addresses)

    def media_paths(self) -> MediaPaths:
        self._require_open()

        return MediaPaths(
            pictures=self._media_root / "pictures",
            videos=self._media_root / "videos",
            sounds=self._media_root / "sounds",
        )

    def ensure_media_paths(self) -> MediaPaths:
        self._require_open()
        paths = self.media_paths()

        try:
            for path in paths.all:
                path.mkdir(
                    parents=True,
                    exist_ok=True,
                )
        except OSError as exc:
            raise SystemError(f"failed to create media directories: {exc}") from exc

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

        messages = tuple(
            f"missing media directory: {path}"
            for path in media.all
            if not path.exists()
        )

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
