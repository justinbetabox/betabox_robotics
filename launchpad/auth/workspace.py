from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class MediaWorkspace:
    pictures: Path
    videos: Path
    sounds: Path

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

    return Workspace(
        root=root,
        curriculum=root / "curriculum",
        media=MediaWorkspace(
            pictures=root / "media" / "pictures",
            videos=root / "media" / "videos",
            sounds=root / "media" / "sounds",
        ),
        preferences=root / "preferences",
        persistent=persistent,
    )
