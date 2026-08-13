from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _validate_path(
    value: object,
    *,
    name: str,
) -> Path:
    if not isinstance(
        value,
        Path,
    ):
        raise TypeError(f"{name} must be a Path")

    return value


@dataclass(
    slots=True,
    frozen=True,
)
class MediaWorkspace:
    pictures: Path
    videos: Path
    sounds: Path

    def __post_init__(
        self,
    ) -> None:
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

    def directories(self) -> tuple[Path, ...]:
        return (
            self.pictures,
            self.videos,
            self.sounds,
        )


@dataclass(slots=True, frozen=True)
class Workspace:
    """Filesystem locations for the current Launchpad user."""

    root: Path
    curriculum: Path
    media: MediaWorkspace
    preferences: Path
    persistent: bool

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "root",
            _validate_path(
                self.root,
                name="root",
            ),
        )

        object.__setattr__(
            self,
            "curriculum",
            _validate_path(
                self.curriculum,
                name="curriculum",
            ),
        )

        object.__setattr__(
            self,
            "preferences",
            _validate_path(
                self.preferences,
                name="preferences",
            ),
        )

    def directories(self) -> tuple[Path, ...]:
        """Return every directory owned by this workspace."""

        return (
            self.root,
            self.curriculum,
            *self.media.directories(),
            self.preferences,
        )

    def ensure_exists(self) -> None:
        """Create any missing workspace directories."""

        for directory in self.directories():
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )


def build_workspace(
    root: Path,
    *,
    persistent: bool,
) -> Workspace:
    """Build a Launchpad workspace rooted at the given directory."""

    root_value = _validate_path(
        root,
        name="root",
    )

    return Workspace(
        root=root_value,
        curriculum=root_value / "curriculum",
        media=MediaWorkspace(
            pictures=root_value / "media" / "pictures",
            videos=root_value / "media" / "videos",
            sounds=root_value / "media" / "sounds",
        ),
        preferences=root_value / "preferences",
        persistent=persistent,
    )
