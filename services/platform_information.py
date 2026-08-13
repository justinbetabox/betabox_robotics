from __future__ import annotations

import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.platform_summary import (
    collect_platform_summary,
)
from betabox_robotics.version import __version__

JSONValue = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


def _validate_config(
    value: object,
) -> PlatformConfig:
    if not isinstance(
        value,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    return value


def _validate_string(
    value: object,
    *,
    name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
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
    if isinstance(value, bool) or not isinstance(
        value,
        str | Path,
    ):
        raise TypeError(f"{name} must be a string or Path")

    if isinstance(value, str):
        value = value.strip()

        if not value:
            raise ValueError(f"{name} cannot be empty")

    return Path(value).expanduser()


def _validate_port(
    value: object,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("port must be an integer")

    if not 1 <= value <= 65535:
        raise ValueError("port must be between 1 and 65535")

    return value


def _validate_flag(
    value: object,
    *,
    name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(f"{name} must be a boolean")

    return value


@dataclass(frozen=True, slots=True)
class RobotInformation:
    """
    Safe, student-facing identity information.
    """

    model: str
    hostname: str
    identifier: str | None
    control_available: bool

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "model",
            _validate_string(
                self.model,
                name="model",
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

        if self.identifier is not None:
            object.__setattr__(
                self,
                "identifier",
                _validate_string(
                    self.identifier,
                    name="identifier",
                ),
            )

        _ = _validate_flag(
            self.control_available,
            name="control_available",
        )


@dataclass(frozen=True, slots=True)
class NetworkInformation:
    hostname: str
    ip_addresses: tuple[str, ...]
    launchpad_urls: tuple[str, ...]
    jupyterhub_urls: tuple[str, ...]
    vision_urls: tuple[str, ...]

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "hostname",
            _validate_string(
                self.hostname,
                name="hostname",
            ),
        )

        for name in (
            "ip_addresses",
            "launchpad_urls",
            "jupyterhub_urls",
            "vision_urls",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            if not isinstance(
                value,
                tuple,
            ):
                raise TypeError(f"{name} must be a tuple")

            values = cast(
                tuple[object, ...],
                value,
            )

            normalized = tuple(
                _validate_string(
                    item,
                    name=f"{name} item",
                )
                for item in values
            )

            object.__setattr__(
                self,
                name,
                normalized,
            )


@dataclass(frozen=True, slots=True)
class SoftwareInformation:
    """
    Installed software information useful for troubleshooting.
    """

    betabox_robotics_version: str
    python_version: str
    operating_system: str
    architecture: str

    def __post_init__(self) -> None:
        for name in (
            "betabox_robotics_version",
            "python_version",
            "operating_system",
            "architecture",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            object.__setattr__(
                self,
                name,
                _validate_string(
                    value,
                    name=name,
                ),
            )


@dataclass(frozen=True, slots=True)
class StorageInformation:
    """
    Filesystem capacity for the primary platform disk.
    """

    total_bytes: int
    used_bytes: int
    available_bytes: int
    used_percent: float

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "total_bytes",
            "used_bytes",
            "available_bytes",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(f"{name} must be an integer")

            if value < 0:
                raise ValueError(f"{name} cannot be negative")

        used_percent = float(self.used_percent)

        if not 0.0 <= used_percent <= 100.0:
            raise ValueError("used_percent must be between 0.0 and 100.0")

        object.__setattr__(
            self,
            "used_percent",
            used_percent,
        )


@dataclass(frozen=True, slots=True)
class MediaLocationInformation:
    """
    Availability of student media locations.

    Raw absolute paths are intentionally not exposed through the
    student-facing API.
    """

    pictures_available: bool
    videos_available: bool
    sounds_available: bool

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "pictures_available",
            "videos_available",
            "sounds_available",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            _ = _validate_flag(
                value,
                name=name,
            )


@dataclass(frozen=True, slots=True)
class FeatureInformation:
    """
    High-level platform feature availability.
    """

    vision_service_available: bool
    camera_ready: bool
    jupyterhub_available: bool

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "vision_service_available",
            "camera_ready",
            "jupyterhub_available",
        ):
            value = cast(
                object,
                getattr(
                    self,
                    name,
                ),
            )

            _ = _validate_flag(
                value,
                name=name,
            )


@dataclass(frozen=True, slots=True)
class PlatformInformationReport:
    """
    Safe information report shared by Launchpad consumers.
    """

    robot: RobotInformation
    network: NetworkInformation
    software: SoftwareInformation
    storage: StorageInformation
    media: MediaLocationInformation
    features: FeatureInformation

    def to_dict(
        self,
    ) -> dict[str, JSONValue]:
        return cast(
            dict[str, JSONValue],
            asdict(self),
        )


def robot_identifier(
    hostname: str,
    *,
    prefix: str,
) -> str | None:
    hostname_value = _validate_string(
        hostname,
        name="hostname",
    )
    prefix_value = _validate_string(
        prefix,
        name="prefix",
    )

    expected_prefix = f"{prefix_value}-"

    if not hostname_value.lower().startswith(expected_prefix.lower()):
        return None

    identifier = hostname_value[len(expected_prefix) :].strip()

    return identifier or None


def public_urls(
    *,
    hostname: str,
    ip_addresses: list[str] | tuple[str, ...],
    port: int,
) -> tuple[str, ...]:
    hostname_value = _validate_string(
        hostname,
        name="hostname",
    )
    port_value = _validate_port(port)

    hosts: list[str] = []

    local_hostname = (
        hostname_value
        if hostname_value.lower().endswith(".local")
        else f"{hostname_value}.local"
    )

    hosts.append(local_hostname)

    for address in ip_addresses:
        address_value = _validate_string(
            address,
            name="ip address",
        )

        if address_value in (
            "0.0.0.0",
            "127.0.0.1",
            "::",
            "::1",
        ):
            continue

        if address_value not in hosts:
            hosts.append(address_value)

    return tuple(
        (
            f"http://[{host}]:{port_value}"
            if ":" in host
            else f"http://{host}:{port_value}"
        )
        for host in hosts
    )


def collect_storage_information(
    path: str | Path,
) -> StorageInformation:
    path_value = _validate_path(
        path,
        name="path",
    )

    try:
        usage = shutil.disk_usage(path_value)
    except OSError:
        return StorageInformation(
            total_bytes=0,
            used_bytes=0,
            available_bytes=0,
            used_percent=0.0,
        )

    used_percent = usage.used / usage.total * 100.0 if usage.total > 0 else 0.0

    return StorageInformation(
        total_bytes=usage.total,
        used_bytes=usage.used,
        available_bytes=usage.free,
        used_percent=round(
            used_percent,
            1,
        ),
    )


def directory_available(
    path: str | Path,
) -> bool:
    path_value = _validate_path(
        path,
        name="path",
    )

    try:
        return path_value.exists() and path_value.is_dir()
    except OSError:
        return False


def operating_system_name() -> str:
    system = platform.system().strip()
    release = platform.release().strip()

    if system and release:
        return f"{system} {release}"

    return system or "Unknown"


def collect_platform_information(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> PlatformInformationReport:
    config_value = _validate_config(config)

    summary = collect_platform_summary(config_value)

    hostname = _validate_string(
        summary.hostname,
        name="hostname",
    )

    addresses = tuple(
        dict.fromkeys(
            address.strip()
            for address in summary.ip_addresses
            if (
                address.strip()
                and ":" not in address
                and not address.startswith("127.")
                and address != "0.0.0.0"
            )
        )
    )

    vision = summary.hardware.vision

    camera_ready = (
        vision.service_available and vision.camera_running and vision.camera_has_frame
    )

    return PlatformInformationReport(
        robot=RobotInformation(
            model="Betabox Car",
            hostname=hostname,
            identifier=robot_identifier(
                hostname,
                prefix=(config_value.network.identity_prefix),
            ),
            control_available=(summary.control.available),
        ),
        network=NetworkInformation(
            hostname=hostname,
            ip_addresses=addresses,
            launchpad_urls=public_urls(
                hostname=hostname,
                ip_addresses=addresses,
                port=(config_value.network.launchpad_port),
            ),
            jupyterhub_urls=public_urls(
                hostname=hostname,
                ip_addresses=addresses,
                port=(config_value.network.jupyterhub_port),
            ),
            vision_urls=public_urls(
                hostname=hostname,
                ip_addresses=addresses,
                port=(config_value.network.vision_port),
            ),
        ),
        software=SoftwareInformation(
            betabox_robotics_version=(__version__),
            python_version=(platform.python_version()),
            operating_system=(operating_system_name()),
            architecture=(platform.machine().strip() or "Unknown"),
        ),
        storage=collect_storage_information(config_value.health.disk_path),
        media=MediaLocationInformation(
            pictures_available=(directory_available(config_value.paths.pictures_dir)),
            videos_available=(directory_available(config_value.paths.videos_dir)),
            sounds_available=(directory_available(config_value.paths.sounds_dir)),
        ),
        features=FeatureInformation(
            vision_service_available=(vision.service_available),
            camera_ready=camera_ready,
            jupyterhub_available=(summary.jupyterhub_proxy_available),
        ),
    )
