from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.services.install_checks.media import (
    check_account_workspace,
    check_media_root,
    check_runtime_media,
)
from betabox_robotics.services.install_checks.models import (
    CheckResult,
)

MODULE = "betabox_robotics.services.install_checks.media"


def create_media_tree(
    media_root: Path,
) -> None:
    pictures = media_root / "pictures"
    videos = media_root / "videos"
    sounds = media_root / "sounds"

    pictures.mkdir(
        parents=True,
    )
    videos.mkdir()
    sounds.mkdir()

    (sounds / "car-honk.mp3").write_bytes(b"audio")


class CheckMediaRootTests(unittest.TestCase):
    def test_accepts_complete_media_tree(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir) / "media"
            create_media_tree(media_root)

            result = check_media_root(
                "runtime-media:picar",
                media_root,
            )

        self.assertEqual(
            result,
            CheckResult(
                name="runtime-media:picar",
                ok=True,
                message=str(media_root),
            ),
        )

    def test_uses_success_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir) / "media"
            create_media_tree(media_root)

            result = check_media_root(
                "workspace:student",
                media_root,
                success_message=(" /home/student "),
            )

        self.assertEqual(
            result,
            CheckResult(
                name="workspace:student",
                ok=True,
                message="/home/student",
            ),
        )

    def test_accepts_string_media_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir) / "media"
            create_media_tree(media_root)

            result = check_media_root(
                "media:test",
                str(media_root),
            )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            str(media_root),
        )

    def test_strips_check_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir) / "media"
            create_media_tree(media_root)

            result = check_media_root(
                " media:test ",
                media_root,
            )

        self.assertEqual(
            result.name,
            "media:test",
        )

    def test_reports_all_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir) / "media"

            result = check_media_root(
                "media:test",
                media_root,
            )

        required = (
            media_root / "pictures",
            media_root / "videos",
            media_root / "sounds",
            (media_root / "sounds" / "car-honk.mp3"),
        )

        self.assertEqual(
            result,
            CheckResult(
                name="media:test",
                ok=False,
                message="; ".join(f"{path}: missing" for path in required),
            ),
        )

    def test_reports_missing_honk_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir) / "media"

            (media_root / "pictures").mkdir(parents=True)
            (media_root / "videos").mkdir()
            (media_root / "sounds").mkdir()

            result = check_media_root(
                "media:test",
                media_root,
            )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            (f"{media_root / 'sounds' / 'car-honk.mp3'}: missing"),
        )

    def test_checks_required_paths_in_order(
        self,
    ) -> None:
        media_root = Path("/home/picar/media")

        with patch.object(
            Path,
            "exists",
            return_value=True,
        ) as exists:
            result = check_media_root(
                "runtime-media:picar",
                media_root,
            )

        self.assertTrue(result.ok)
        self.assertEqual(
            exists.call_args_list,
            [
                call(),
                call(),
                call(),
                call(),
            ],
        )

    def test_reports_permission_error(self) -> None:
        media_root = Path("/home/picar/media")
        required = (
            media_root / "pictures",
            media_root / "videos",
            media_root / "sounds",
            (media_root / "sounds" / "car-honk.mp3"),
        )

        with patch.object(
            Path,
            "exists",
            side_effect=[
                PermissionError(),
                True,
                True,
                True,
            ],
        ):
            result = check_media_root(
                "runtime-media:picar",
                media_root,
            )

        self.assertEqual(
            result,
            CheckResult(
                name="runtime-media:picar",
                ok=False,
                message=(f"{required[0]}: permission denied"),
            ),
        )

    def test_continues_after_permission_error(
        self,
    ) -> None:
        media_root = Path("/home/picar/media")
        pictures = media_root / "pictures"
        sounds = media_root / "sounds"

        with patch.object(
            Path,
            "exists",
            side_effect=[
                PermissionError(),
                True,
                False,
                True,
            ],
        ):
            result = check_media_root(
                "runtime-media:picar",
                media_root,
            )

        self.assertEqual(
            result.message,
            (f"{pictures}: permission denied; {sounds}: missing"),
        )

    def test_reports_os_error(self) -> None:
        media_root = Path("/home/picar/media")
        videos = media_root / "videos"

        with patch.object(
            Path,
            "exists",
            side_effect=[
                True,
                OSError("filesystem failed"),
                True,
                True,
            ],
        ):
            result = check_media_root(
                "runtime-media:picar",
                media_root,
            )

        self.assertEqual(
            result,
            CheckResult(
                name="runtime-media:picar",
                ok=False,
                message=(f"{videos}: filesystem failed"),
            ),
        )

    def test_unexpected_filesystem_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "exists",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_media_root(
                "media:test",
                "/media",
            )

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_name_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                "name must be a string",
            ),
        ):
            check_media_root(
                None,  # type: ignore[arg-type]
                "/media",
            )

        exists.assert_not_called()

    def test_rejects_empty_name_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                ValueError,
                "name cannot be empty",
            ),
        ):
            check_media_root(
                " ",
                "/media",
            )

        exists.assert_not_called()

    def test_rejects_invalid_media_root_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("media_root must be a string or Path"),
            ),
        ):
            check_media_root(
                "media:test",
                True,  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_rejects_invalid_success_message_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("success_message must be a string"),
            ),
        ):
            check_media_root(
                "media:test",
                "/media",
                success_message=123,  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_rejects_empty_success_message_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                ValueError,
                ("success_message cannot be empty"),
            ),
        ):
            check_media_root(
                "media:test",
                "/media",
                success_message=" ",
            )

        exists.assert_not_called()


class CheckRuntimeMediaTests(unittest.TestCase):
    def test_checks_service_user_media_tree(
        self,
    ) -> None:
        user = SimpleNamespace(pw_dir="/home/picar")
        expected = CheckResult(
            name="runtime-media:picar",
            ok=True,
            message="/home/picar/media",
        )

        with (
            patch(
                f"{MODULE}.pwd.getpwnam",
                return_value=user,
            ) as getpwnam,
            patch(
                f"{MODULE}.check_media_root",
                return_value=expected,
            ) as check_root,
        ):
            result = check_runtime_media(" picar ")

        self.assertIs(
            result,
            expected,
        )
        getpwnam.assert_called_once_with("picar")
        check_root.assert_called_once_with(
            "runtime-media:picar",
            Path("/home/picar/media"),
        )

    def test_reports_missing_service_user(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.pwd.getpwnam",
            side_effect=KeyError("missing"),
        ):
            result = check_runtime_media("picar")

        self.assertEqual(
            result,
            CheckResult(
                name="runtime-media:picar",
                ok=False,
                message=("service user does not exist"),
            ),
        )

    def test_reports_user_lookup_os_error(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.pwd.getpwnam",
            side_effect=OSError("account database failed"),
        ):
            result = check_runtime_media("picar")

        self.assertEqual(
            result,
            CheckResult(
                name="runtime-media:picar",
                ok=False,
                message=("account database failed"),
            ),
        )

    def test_unexpected_lookup_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.pwd.getpwnam",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_runtime_media("picar")

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_username_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.pwd.getpwnam") as getpwnam,
            self.assertRaisesRegex(
                TypeError,
                "username must be a string",
            ),
        ):
            check_runtime_media(
                None  # type: ignore[arg-type]
            )

        getpwnam.assert_not_called()

    def test_rejects_empty_username_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.pwd.getpwnam") as getpwnam,
            self.assertRaisesRegex(
                ValueError,
                "username cannot be empty",
            ),
        ):
            check_runtime_media(" ")

        getpwnam.assert_not_called()

    def test_media_check_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.pwd.getpwnam",
                return_value=SimpleNamespace(pw_dir="/home/picar"),
            ),
            patch(
                f"{MODULE}.check_media_root",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_runtime_media("picar")

        self.assertIs(
            context.exception,
            error,
        )


class CheckAccountWorkspaceTests(unittest.TestCase):
    def test_checks_managed_account_workspace(
        self,
    ) -> None:
        home = Path("/home/student")
        expected = CheckResult(
            name="workspace:student",
            ok=True,
            message=str(home),
        )

        with patch(
            f"{MODULE}.check_media_root",
            return_value=expected,
        ) as check_root:
            result = check_account_workspace(
                " student ",
                home,
            )

        self.assertIs(
            result,
            expected,
        )
        check_root.assert_called_once_with(
            "workspace:student",
            home / "media",
            success_message=str(home),
        )

    def test_accepts_string_home(self) -> None:
        expected = CheckResult(
            name="workspace:student",
            ok=True,
            message="/home/student",
        )

        with patch(
            f"{MODULE}.check_media_root",
            return_value=expected,
        ) as check_root:
            result = check_account_workspace(
                "student",
                "/home/student",
            )

        self.assertIs(
            result,
            expected,
        )
        check_root.assert_called_once_with(
            "workspace:student",
            Path("/home/student/media"),
            success_message="/home/student",
        )

    def test_rejects_invalid_username_before_media_check(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_media_root") as check_root,
            self.assertRaisesRegex(
                TypeError,
                "username must be a string",
            ),
        ):
            check_account_workspace(
                None,  # type: ignore[arg-type]
                "/home/student",
            )

        check_root.assert_not_called()

    def test_rejects_empty_username_before_media_check(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_media_root") as check_root,
            self.assertRaisesRegex(
                ValueError,
                "username cannot be empty",
            ),
        ):
            check_account_workspace(
                " ",
                "/home/student",
            )

        check_root.assert_not_called()

    def test_rejects_invalid_home_before_media_check(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_media_root") as check_root,
            self.assertRaisesRegex(
                TypeError,
                "home must be a string or Path",
            ),
        ):
            check_account_workspace(
                "student",
                True,  # type: ignore[arg-type]
            )

        check_root.assert_not_called()

    def test_media_check_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.check_media_root",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_account_workspace(
                "student",
                "/home/student",
            )

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
