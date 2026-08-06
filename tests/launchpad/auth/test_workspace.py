from __future__ import annotations

import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import call, patch

from betabox_robotics.launchpad.auth.workspace import (
    MediaWorkspace,
    Workspace,
    _validate_path,
    build_workspace,
)


class ValidatePathTests(unittest.TestCase):
    def test_accepts_path(
        self,
    ) -> None:
        path = Path("/tmp/workspace")

        self.assertIs(
            _validate_path(
                path,
                name="path",
            ),
            path,
        )

    def test_rejects_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "path must be a Path",
        ):
            _validate_path(
                "/tmp/workspace",
                name="path",
            )

    def test_rejects_other_types(
        self,
    ) -> None:
        for value in (
            None,
            True,
            1,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "path must be a Path",
                ),
            ):
                _validate_path(
                    value,
                    name="path",
                )


class MediaWorkspaceTests(unittest.TestCase):
    def test_constructs_valid_workspace(
        self,
    ) -> None:
        media = MediaWorkspace(
            pictures=Path(
                "/home/student/media/pictures"
            ),
            videos=Path(
                "/home/student/media/videos"
            ),
            sounds=Path(
                "/home/student/media/sounds"
            ),
        )

        self.assertEqual(
            media.pictures,
            Path(
                "/home/student/media/pictures"
            ),
        )
        self.assertEqual(
            media.videos,
            Path(
                "/home/student/media/videos"
            ),
        )
        self.assertEqual(
            media.sounds,
            Path(
                "/home/student/media/sounds"
            ),
        )

    def test_directories_returns_expected_order(
        self,
    ) -> None:
        pictures = Path(
            "/workspace/media/pictures"
        )
        videos = Path(
            "/workspace/media/videos"
        )
        sounds = Path(
            "/workspace/media/sounds"
        )
        media = MediaWorkspace(
            pictures=pictures,
            videos=videos,
            sounds=sounds,
        )

        self.assertEqual(
            media.directories(),
            (
                pictures,
                videos,
                sounds,
            ),
        )

    def test_rejects_invalid_pictures(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "pictures must be a Path",
        ):
            MediaWorkspace(
                pictures="pictures",  # type: ignore[arg-type]
                videos=Path("videos"),
                sounds=Path("sounds"),
            )

    def test_rejects_invalid_videos(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "videos must be a Path",
        ):
            MediaWorkspace(
                pictures=Path("pictures"),
                videos="videos",  # type: ignore[arg-type]
                sounds=Path("sounds"),
            )

    def test_rejects_invalid_sounds(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "sounds must be a Path",
        ):
            MediaWorkspace(
                pictures=Path("pictures"),
                videos=Path("videos"),
                sounds="sounds",  # type: ignore[arg-type]
            )

    def test_is_frozen(
        self,
    ) -> None:
        media = MediaWorkspace(
            pictures=Path("pictures"),
            videos=Path("videos"),
            sounds=Path("sounds"),
        )

        with self.assertRaises(
            FrozenInstanceError,
        ):
            media.pictures = Path(  # type: ignore[misc]
                "changed"
            )

    def test_is_slotted(
        self,
    ) -> None:
        media = MediaWorkspace(
            pictures=Path("pictures"),
            videos=Path("videos"),
            sounds=Path("sounds"),
        )

        self.assertFalse(
            hasattr(
                media,
                "__dict__",
            )
        )


class WorkspaceConstructionTests(unittest.TestCase):
    def setUp(
        self,
    ) -> None:
        self.root = Path(
            "/home/student"
        )
        self.media = MediaWorkspace(
            pictures=(
                self.root
                / "media"
                / "pictures"
            ),
            videos=(
                self.root
                / "media"
                / "videos"
            ),
            sounds=(
                self.root
                / "media"
                / "sounds"
            ),
        )

    def test_constructs_valid_workspace(
        self,
    ) -> None:
        workspace = Workspace(
            root=self.root,
            curriculum=(
                self.root
                / "curriculum"
            ),
            media=self.media,
            preferences=(
                self.root
                / "preferences"
            ),
            persistent=True,
        )

        self.assertEqual(
            workspace.root,
            self.root,
        )
        self.assertEqual(
            workspace.curriculum,
            (
                self.root
                / "curriculum"
            ),
        )
        self.assertIs(
            workspace.media,
            self.media,
        )
        self.assertEqual(
            workspace.preferences,
            (
                self.root
                / "preferences"
            ),
        )
        self.assertTrue(
            workspace.persistent,
        )

    def test_rejects_invalid_root(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "root must be a Path",
        ):
            Workspace(
                root="/home/student",  # type: ignore[arg-type]
                curriculum=Path(
                    "/home/student/curriculum"
                ),
                media=self.media,
                preferences=Path(
                    "/home/student/preferences"
                ),
                persistent=True,
            )

    def test_rejects_invalid_curriculum(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "curriculum must be a Path",
        ):
            Workspace(
                root=self.root,
                curriculum="curriculum",  # type: ignore[arg-type]
                media=self.media,
                preferences=(
                    self.root
                    / "preferences"
                ),
                persistent=True,
            )

    def test_rejects_invalid_media(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "media must be a MediaWorkspace",
        ):
            Workspace(
                root=self.root,
                curriculum=(
                    self.root
                    / "curriculum"
                ),
                media=object(),  # type: ignore[arg-type]
                preferences=(
                    self.root
                    / "preferences"
                ),
                persistent=True,
            )

    def test_rejects_invalid_preferences(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "preferences must be a Path",
        ):
            Workspace(
                root=self.root,
                curriculum=(
                    self.root
                    / "curriculum"
                ),
                media=self.media,
                preferences="preferences",  # type: ignore[arg-type]
                persistent=True,
            )

    def test_rejects_invalid_persistent(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "persistent must be a boolean",
        ):
            Workspace(
                root=self.root,
                curriculum=(
                    self.root
                    / "curriculum"
                ),
                media=self.media,
                preferences=(
                    self.root
                    / "preferences"
                ),
                persistent=1,  # type: ignore[arg-type]
            )

    def test_directories_returns_expected_order(
        self,
    ) -> None:
        workspace = Workspace(
            root=self.root,
            curriculum=(
                self.root
                / "curriculum"
            ),
            media=self.media,
            preferences=(
                self.root
                / "preferences"
            ),
            persistent=False,
        )

        self.assertEqual(
            workspace.directories(),
            (
                self.root,
                self.root / "curriculum",
                self.root / "media" / "pictures",
                self.root / "media" / "videos",
                self.root / "media" / "sounds",
                self.root / "preferences",
            ),
        )

    def test_is_frozen(
        self,
    ) -> None:
        workspace = Workspace(
            root=self.root,
            curriculum=(
                self.root
                / "curriculum"
            ),
            media=self.media,
            preferences=(
                self.root
                / "preferences"
            ),
            persistent=True,
        )

        with self.assertRaises(
            FrozenInstanceError,
        ):
            workspace.persistent = False  # type: ignore[misc]

    def test_is_slotted(
        self,
    ) -> None:
        workspace = Workspace(
            root=self.root,
            curriculum=(
                self.root
                / "curriculum"
            ),
            media=self.media,
            preferences=(
                self.root
                / "preferences"
            ),
            persistent=True,
        )

        self.assertFalse(
            hasattr(
                workspace,
                "__dict__",
            )
        )


class EnsureExistsTests(unittest.TestCase):
    def test_creates_all_directories(
        self,
    ) -> None:
        workspace = build_workspace(
            Path(
                "/home/student"
            ),
            persistent=True,
        )

        with patch.object(
            Path,
            "mkdir",
        ) as mkdir:
            workspace.ensure_exists()

        self.assertEqual(
            mkdir.call_args_list,
            [
                call(
                    parents=True,
                    exist_ok=True,
                ),
                call(
                    parents=True,
                    exist_ok=True,
                ),
                call(
                    parents=True,
                    exist_ok=True,
                ),
                call(
                    parents=True,
                    exist_ok=True,
                ),
                call(
                    parents=True,
                    exist_ok=True,
                ),
                call(
                    parents=True,
                    exist_ok=True,
                ),
            ],
        )

    def test_creates_real_directory_layout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = (
                Path(temp)
                / "student"
            )
            workspace = build_workspace(
                root,
                persistent=True,
            )

            workspace.ensure_exists()

            for directory in (
                workspace.directories()
            ):
                with self.subTest(
                    directory=directory,
                ):
                    self.assertTrue(
                        directory.is_dir()
                    )

    def test_is_idempotent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = build_workspace(
                Path(temp)
                / "guest",
                persistent=False,
            )

            workspace.ensure_exists()
            workspace.ensure_exists()

            for directory in (
                workspace.directories()
            ):
                self.assertTrue(
                    directory.is_dir()
                )

    def test_filesystem_error_propagates(
        self,
    ) -> None:
        workspace = build_workspace(
            Path(
                "/home/student"
            ),
            persistent=True,
        )
        error = OSError(
            "permission denied"
        )

        with (
            patch.object(
                Path,
                "mkdir",
                side_effect=error,
            ),
            self.assertRaises(
                OSError
            ) as context,
        ):
            workspace.ensure_exists()

        self.assertIs(
            context.exception,
            error,
        )


class BuildWorkspaceTests(unittest.TestCase):
    def test_builds_expected_layout(
        self,
    ) -> None:
        root = Path(
            "/home/student1"
        )

        workspace = build_workspace(
            root,
            persistent=True,
        )

        self.assertEqual(
            workspace,
            Workspace(
                root=root,
                curriculum=(
                    root
                    / "curriculum"
                ),
                media=MediaWorkspace(
                    pictures=(
                        root
                        / "media"
                        / "pictures"
                    ),
                    videos=(
                        root
                        / "media"
                        / "videos"
                    ),
                    sounds=(
                        root
                        / "media"
                        / "sounds"
                    ),
                ),
                preferences=(
                    root
                    / "preferences"
                ),
                persistent=True,
            ),
        )

    def test_builds_temporary_guest_workspace(
        self,
    ) -> None:
        workspace = build_workspace(
            Path(
                "/home/guest"
            ),
            persistent=False,
        )

        self.assertFalse(
            workspace.persistent,
        )
        self.assertEqual(
            workspace.root,
            Path(
                "/home/guest"
            ),
        )

    def test_rejects_invalid_root(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "root must be a Path",
        ):
            build_workspace(
                "/home/student",  # type: ignore[arg-type]
                persistent=True,
            )

    def test_rejects_invalid_persistent(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "persistent must be a boolean",
        ):
            build_workspace(
                Path(
                    "/home/student"
                ),
                persistent=1,  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
