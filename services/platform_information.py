from __future__ import annotations

import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)
from betabox_robotics.services.platform_summary import (
    collect_platform_summary,
)
from betabox_robotics.version import __version__


@dataclass(frozen=True)
class RobotInformation:
    """
    Safe, student-facing identity information.
    """

    model: str
    hostname: str
    identifier: str | None
    control_available: bool


@dataclass(frozen=True)
class NetworkInformation:
    """
    Student-facing network endpoints.

    This intentionally excludes credentials, connection profiles,
    interfaces, and other administrative network configuration.
    """

    hostname: str
    ip_addresses: list[str]
    launchpad_urls: list[str]
    jupyterhub_urls: list[str]
    vision_urls: list[str]


@dataclass(frozen=True)
class SoftwareInformation:
    """
    Installed software information useful for troubleshooting.
    """

    betabox_robotics_version: str
    python_version: str
    operating_system: str
    architecture: str


@dataclass(frozen=True)
class StorageInformation:
    """
    Filesystem capacity for the primary platform disk.
    """

    total_bytes: int
    used_bytes: int
    available_bytes: int
    used_percent: float


@dataclass(frozen=True)
class MediaLocationInformation:
    """
    Availability of student media locations.

    Raw absolute paths are intentionally not exposed through the
    student-facing API.
    """

    pictures_available: bool
    videos_available: bool
    sounds_available: bool


@dataclass(frozen=True)
class FeatureInformation:
    """
    High-level platform feature availability.
    """

    vision_service_available: bool
    camera_ready: bool
    jupyterhub_available: bool


@dataclass(frozen=True)
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def robot_identifier(
    hostname: str,
    *,
    prefix: str,
) -> str | None:
    """
    Extract the short robot identifier from a generated hostname.

    Example:

        Betabox-7eea -> 7eea
    """

    expected_prefix = f"{prefix}-"

    if not hostname.lower().startswith(
        expected_prefix.lower()
    ):
        return None

    identifier = hostname[
        len(expected_prefix):
    ].strip()

    return identifier or None


def public_urls(
    *,
    hostname: str,
    ip_addresses: list[str],
    port: int,
) -> list[str]:
    """
    Build browser-accessible URLs for a platform endpoint.

    Localhost and bind addresses are not returned because they are not
    useful from another classroom computer.
    """

    hosts: list[str] = []

    local_hostname = f"{hostname}.local"

    if local_hostname not in hosts:
        hosts.append(local_hostname)

    for address in ip_addresses:
        if address not in hosts:
            hosts.append(address)

    return [
        f"http://{host}:{port}"
        for host in hosts
    ]


def collect_storage_information(
    path: Path,
) -> StorageInformation:
    """
    Collect disk capacity for the filesystem containing ``path``.
    """

    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return StorageInformation(
            total_bytes=0,
            used_bytes=0,
            available_bytes=0,
            used_percent=0.0,
        )

    used_percent = (
        usage.used / usage.total * 100.0
        if usage.total > 0
        else 0.0
    )

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
    path: Path,
) -> bool:
    """
    Return whether a configured media directory is usable.
    """

    try:
        return (
            path.exists()
            and path.is_dir()
        )
    except OSError:
        return False


def operating_system_name() -> str:
    """
    Return a friendly operating-system description.
    """

    system = platform.system()
    release = platform.release()

    if system and release:
        return f"{system} {release}"

    return system or "Unknown"


def collect_platform_information(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> PlatformInformationReport:
    """
    Collect safe, student-facing platform information.

    The complete PlatformConfig is deliberately not serialized.
    """

    summary = collect_platform_summary(
        config
    )

    hostname = summary.hostname
    addresses = [
        address
        for address in summary.ip_addresses
        if ":" not in address
    ]

    vision = summary.hardware.vision

    camera_ready = (
        vision.service_available
        and vision.camera_running
        and vision.camera_has_frame
    )

    robot_control_available = (
        summary.control.available
    )

    return PlatformInformationReport(
        robot=RobotInformation(
            model="Betabox Car",
            hostname=hostname,
            identifier=robot_identifier(
                hostname,
                prefix=(
                    config.network
                    .identity_prefix
                ),
            ),
            control_available=(
                robot_control_available
            ),
        ),
        network=NetworkInformation(
            hostname=hostname,
            ip_addresses=addresses,
            launchpad_urls=public_urls(
                hostname=hostname,
                ip_addresses=addresses,
                port=(
                    config.network
                    .launchpad_port
                ),
            ),
            jupyterhub_urls=public_urls(
                hostname=hostname,
                ip_addresses=addresses,
                port=(
                    config.network
                    .jupyterhub_port
                ),
            ),
            vision_urls=public_urls(
                hostname=hostname,
                ip_addresses=addresses,
                port=(
                    config.network
                    .vision_port
                ),
            ),
        ),
        software=SoftwareInformation(
            betabox_robotics_version=(
                __version__
            ),
            python_version=(
                platform.python_version()
            ),
            operating_system=(
                operating_system_name()
            ),
            architecture=(
                platform.machine()
                or "Unknown"
            ),
        ),
        storage=collect_storage_information(
            config.health.disk_path
        ),
        media=MediaLocationInformation(
            pictures_available=(
                directory_available(
                    config.paths.pictures_dir
                )
            ),
            videos_available=(
                directory_available(
                    config.paths.videos_dir
                )
            ),
            sounds_available=(
                directory_available(
                    config.paths.sounds_dir
                )
            ),
        ),
        features=FeatureInformation(
            vision_service_available=(
                vision.service_available
            ),
            camera_ready=(
                camera_ready
            ),
            jupyterhub_available=(
                summary
                .jupyterhub_proxy_available
            ),
        ),
    )
