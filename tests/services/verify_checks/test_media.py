from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.verify_checks.media import (
    check_media_path,
    check_media_paths,
)
from betabox_robotics.services.verify_checks.models import (
    CheckResult,
)

MODULE = "betabox_robotics.services.verify_checks.media"


class CheckMediaPathTests(unittest.TestCase):
    def test_reports_existing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pictures"
            path.mkdir()

            result = check_media_path(path)

        self.assertEqual(
            result,
            CheckResult(
                name="media:pictures",
                ok=True,
                message=str(path),
            ),
        )

    def test_accepts_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pictures"
            path.write_text(
                "not a directory",
                encoding="utf-8",
            )

            result = check_media_path(path)

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            str(path),
        )

    def test_reports_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pictures"

            result = check_media_path(path)

        self.assertEqual(
            result,
            CheckResult(
                name="media:pictures",
                ok=False,
                message=f"missing {path}",
            ),
        )

    def test_accepts_string_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sounds"
            path.mkdir()

            result = check_media_path(str(path))

        self.assertEqual(
            result.name,
            "media:sounds",
        )
        self.assertTrue(result.ok)

    def test_expands_user_path(self) -> None:
        expanded = Path("/home/picar/media/pictures")

        with (
            patch.object(
                Path,
                "expanduser",
                return_value=expanded,
            ) as expanduser,
            patch.object(
                Path,
                "exists",
                return_value=True,
            ) as exists,
        ):
            result = check_media_path("~/media/pictures")

        expanduser.assert_called_once_with()
        exists.assert_called_once_with()
        self.assertEqual(
            result,
            CheckResult(
                name="media:pictures",
                ok=True,
                message=str(expanded),
            ),
        )

    def test_checks_path_once(self) -> None:
        path = Path("/home/picar/media/pictures")

        with patch.object(
            Path,
            "exists",
            return_value=True,
        ) as exists:
            result = check_media_path(path)

        exists.assert_called_once_with()
        self.assertTrue(result.ok)

    def test_reports_filesystem_error(self) -> None:
        path = Path("/home/picar/media/pictures")

        with patch.object(
            Path,
            "exists",
            side_effect=OSError("permission denied"),
        ):
            result = check_media_path(path)

        self.assertEqual(
            result,
            CheckResult(
                name="media:pictures",
                ok=False,
                message="permission denied",
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
            check_media_path("/home/picar/media/pictures")

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_path_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                "path must be a string or Path",
            ),
        ):
            check_media_path(
                True  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_uses_final_path_name(self) -> None:
        with patch.object(
            Path,
            "exists",
            return_value=False,
        ):
            result = check_media_path("/home/picar/media/custom")

        self.assertEqual(
            result.name,
            "media:custom",
        )


class CheckMediaPathsTests(unittest.TestCase):
    def test_checks_all_configured_paths_in_order(
        self,
    ) -> None:
        paths = DEFAULT_PLATFORM_CONFIG.paths

        results = (
            CheckResult(
                name="media:pictures",
                ok=True,
                message=str(paths.pictures_dir),
            ),
            CheckResult(
                name="media:videos",
                ok=True,
                message=str(paths.videos_dir),
            ),
            CheckResult(
                name="media:sounds",
                ok=True,
                message=str(paths.sounds_dir),
            ),
        )

        with patch(
            f"{MODULE}.check_media_path",
            side_effect=results,
        ) as check_path:
            result = check_media_paths(DEFAULT_PLATFORM_CONFIG)

        self.assertEqual(
            result,
            results,
        )
        self.assertIsInstance(
            result,
            tuple,
        )
        self.assertEqual(
            check_path.call_args_list,
            [
                call(paths.pictures_dir),
                call(paths.videos_dir),
                call(paths.sounds_dir),
            ],
        )

    def test_uses_default_config(self) -> None:
        paths = DEFAULT_PLATFORM_CONFIG.paths

        with patch(
            f"{MODULE}.check_media_path",
            side_effect=(
                CheckResult(
                    name="media:pictures",
                    ok=True,
                ),
                CheckResult(
                    name="media:videos",
                    ok=True,
                ),
                CheckResult(
                    name="media:sounds",
                    ok=True,
                ),
            ),
        ) as check_path:
            result = check_media_paths()

        self.assertEqual(
            len(result),
            3,
        )
        self.assertEqual(
            check_path.call_args_list,
            [
                call(paths.pictures_dir),
                call(paths.videos_dir),
                call(paths.sounds_dir),
            ],
        )

    def test_preserves_failed_results(self) -> None:
        paths = DEFAULT_PLATFORM_CONFIG.paths

        expected = (
            CheckResult(
                name="media:pictures",
                ok=True,
                message=str(paths.pictures_dir),
            ),
            CheckResult(
                name="media:videos",
                ok=False,
                message=(f"missing {paths.videos_dir}"),
            ),
            CheckResult(
                name="media:sounds",
                ok=True,
                message=str(paths.sounds_dir),
            ),
        )

        with patch(
            f"{MODULE}.check_media_path",
            side_effect=expected,
        ):
            result = check_media_paths(DEFAULT_PLATFORM_CONFIG)

        self.assertEqual(
            result,
            expected,
        )

    def test_rejects_invalid_config_before_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_media_path") as check_path,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            check_media_paths(
                object()  # type: ignore[arg-type]
            )

        check_path.assert_not_called()

    def test_dependency_error_propagates(self) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.check_media_path",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_media_paths()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
