from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.services.accounts import (
    BETABOX_HARDWARE_GROUPS,
    BETABOX_SHARED_GROUP,
    ProvisionedAccount,
)
from betabox_robotics.services.workspace import (
    WORKSPACE_MODE,
    _set_ownership,
    _validate_id,
    _validate_path,
    _validate_string,
    account_ids,
    create_runtime_media,
    create_workspace,
    ensure_directory,
    group_id,
    install_directory,
    populate_media,
    set_ownership_recursive,
    workspace_directories,
)

MODULE = "betabox_robotics.services.workspace"


def make_account(
    *,
    username: str = "student",
    home: Path = Path("/home/student"),
    install_media: bool = True,
) -> ProvisionedAccount:
    return ProvisionedAccount(
        username=username,
        display_name="Student",
        group=username,
        home=home,
        shell=Path("/bin/bash"),
        supplemental_groups=BETABOX_HARDWARE_GROUPS,
        persistent=True,
        install_media=install_media,
    )


class ValidationHelperTests(unittest.TestCase):
    def test_validate_string(self) -> None:
        self.assertEqual(
            _validate_string(
                " student ",
                name="username",
            ),
            "student",
        )

    def test_validate_string_rejects_invalid_values(self) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "username must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="username",
                )

        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "username cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="username",
                )

    def test_validate_path(self) -> None:
        path = Path("/tmp/workspace")

        self.assertEqual(
            _validate_path(
                path,
                name="path",
            ),
            path,
        )
        self.assertEqual(
            _validate_path(
                "/tmp/workspace",
                name="path",
            ),
            path,
        )

    def test_validate_path_rejects_invalid_type(self) -> None:
        for value in (
            True,
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "path must be a string or Path",
                ),
            ):
                _validate_path(
                    value,
                    name="path",
                )

    def test_validate_id(self) -> None:
        self.assertEqual(
            _validate_id(
                1000,
                name="uid",
            ),
            1000,
        )
        self.assertEqual(
            _validate_id(
                0,
                name="uid",
            ),
            0,
        )

    def test_validate_id_rejects_invalid_values(self) -> None:
        for value in (
            True,
            1.0,
            "1",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "uid must be an integer",
                ),
            ):
                _validate_id(
                    value,
                    name="uid",
                )

        with self.assertRaisesRegex(
            ValueError,
            "uid cannot be negative",
        ):
            _validate_id(
                -1,
                name="uid",
            )


class AccountLookupTests(unittest.TestCase):
    def test_account_ids(self) -> None:
        account = SimpleNamespace(
            pw_uid=1001,
            pw_gid=1002,
        )

        with patch(
            f"{MODULE}.pwd.getpwnam",
            return_value=account,
        ) as lookup:
            result = account_ids(" student ")

        self.assertEqual(
            result,
            (
                1001,
                1002,
            ),
        )
        lookup.assert_called_once_with("student")

    def test_account_ids_rejects_missing_account(self) -> None:
        with (
            patch(
                f"{MODULE}.pwd.getpwnam",
                side_effect=KeyError("missing"),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "Linux account does not exist: student",
            ) as context,
        ):
            account_ids("student")

        self.assertIsInstance(
            context.exception.__cause__,
            KeyError,
        )

    def test_group_id(self) -> None:
        group = SimpleNamespace(gr_gid=2000)

        with patch(
            f"{MODULE}.grp.getgrnam",
            return_value=group,
        ) as lookup:
            result = group_id(" betabox ")

        self.assertEqual(
            result,
            2000,
        )
        lookup.assert_called_once_with("betabox")

    def test_group_id_rejects_missing_group(self) -> None:
        with (
            patch(
                f"{MODULE}.grp.getgrnam",
                side_effect=KeyError("missing"),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "Linux group does not exist: betabox",
            ) as context,
        ):
            group_id("betabox")

        self.assertIsInstance(
            context.exception.__cause__,
            KeyError,
        )


class WorkspaceDirectoryTests(unittest.TestCase):
    def test_workspace_directories(self) -> None:
        account = make_account()

        self.assertEqual(
            workspace_directories(account),
            (
                Path("/home/student/curriculum"),
                Path("/home/student/media"),
                Path("/home/student/media/pictures"),
                Path("/home/student/media/videos"),
                Path("/home/student/media/sounds"),
                Path("/home/student/preferences"),
            ),
        )

    def test_workspace_directories_rejects_invalid_account(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "account must be a ProvisionedAccount",
        ):
            workspace_directories(
                object()  # type: ignore[arg-type]
            )


class EnsureDirectoryTests(unittest.TestCase):
    def test_creates_and_configures_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "workspace" / "media"

            with patch(f"{MODULE}._set_ownership") as set_ownership:
                ensure_directory(
                    directory,
                    uid=1000,
                    gid=2000,
                )

            self.assertTrue(directory.is_dir())
            self.assertEqual(
                directory.stat().st_mode & 0o7777,
                WORKSPACE_MODE,
            )
            set_ownership.assert_called_once_with(
                directory,
                uid=1000,
                gid=2000,
            )

    def test_existing_directory_is_reconfigured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "media"
            directory.mkdir()
            directory.chmod(0o700)

            with patch(f"{MODULE}._set_ownership"):
                ensure_directory(
                    directory,
                    uid=1000,
                    gid=2000,
                )

            self.assertEqual(
                directory.stat().st_mode & 0o7777,
                WORKSPACE_MODE,
            )

    def test_rejects_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "media"
            path.write_text(
                "not a directory",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                ensure_directory(
                    path,
                    uid=1000,
                    gid=2000,
                )

    def test_validates_ids_before_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "media"

            with self.assertRaisesRegex(
                ValueError,
                "uid cannot be negative",
            ):
                ensure_directory(
                    path,
                    uid=-1,
                    gid=2000,
                )

            self.assertFalse(path.exists())


class CreateRuntimeMediaTests(unittest.TestCase):
    def test_creates_runtime_media_tree_and_installs_assets(
        self,
    ) -> None:
        account = SimpleNamespace(
            pw_dir="/home/picar",
            pw_uid=1000,
            pw_gid=1001,
        )
        repository = Path("/opt/libs/betabox_robotics")

        with (
            patch(
                f"{MODULE}.pwd.getpwnam",
                return_value=account,
            ) as lookup,
            patch(f"{MODULE}.ensure_directory") as ensure,
            patch(f"{MODULE}.install_directory") as install,
        ):
            create_runtime_media(
                "picar",
                repository,
            )

        lookup.assert_called_once_with("picar")
        self.assertEqual(
            ensure.call_args_list,
            [
                call(
                    Path("/home/picar/media"),
                    uid=1000,
                    gid=1001,
                ),
                call(
                    Path("/home/picar/media/pictures"),
                    uid=1000,
                    gid=1001,
                ),
                call(
                    Path("/home/picar/media/videos"),
                    uid=1000,
                    gid=1001,
                ),
                call(
                    Path("/home/picar/media/sounds"),
                    uid=1000,
                    gid=1001,
                ),
            ],
        )
        install.assert_called_once_with(
            repository / "deployment" / "assets" / "sounds",
            Path("/home/picar/media/sounds"),
            uid=1000,
            gid=1001,
        )

    def test_rejects_missing_service_account(self) -> None:
        with (
            patch(
                f"{MODULE}.pwd.getpwnam",
                side_effect=KeyError("missing"),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "Linux account does not exist: picar",
            ),
        ):
            create_runtime_media(
                "picar",
                Path("/repository"),
            )


class CreateWorkspaceTests(unittest.TestCase):
    def test_creates_all_workspace_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "student"
            home.mkdir()

            account = make_account(home=home)

            with (
                patch(
                    f"{MODULE}.account_ids",
                    return_value=(
                        1000,
                        1001,
                    ),
                ) as ids,
                patch(
                    f"{MODULE}.group_id",
                    return_value=2000,
                ) as shared_group,
                patch(f"{MODULE}.ensure_directory") as ensure,
            ):
                create_workspace(account)

            ids.assert_called_once_with("student")
            shared_group.assert_called_once_with(BETABOX_SHARED_GROUP)
            self.assertEqual(
                ensure.call_args_list,
                [
                    call(
                        directory,
                        uid=1000,
                        gid=2000,
                    )
                    for directory in workspace_directories(account)
                ],
            )

    def test_rejects_missing_home_directory(self) -> None:
        account = make_account(home=Path("/missing/student"))

        with self.assertRaisesRegex(
            RuntimeError,
            "Account home directory does not exist",
        ):
            create_workspace(account)

    def test_rejects_invalid_account(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "account must be a ProvisionedAccount",
        ):
            create_workspace(
                object()  # type: ignore[arg-type]
            )


class OwnershipTests(unittest.TestCase):
    def test_set_ownership_does_not_follow_symlinks(
        self,
    ) -> None:
        path = Path("/tmp/item")

        with patch(f"{MODULE}.os.chown") as chown:
            _set_ownership(
                path,
                uid=1000,
                gid=2000,
            )

        chown.assert_called_once_with(
            path,
            1000,
            2000,
            follow_symlinks=False,
        )

    def test_recursive_ownership_for_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "file.txt"
            path.write_text(
                "content",
                encoding="utf-8",
            )

            with patch(f"{MODULE}._set_ownership") as ownership:
                set_ownership_recursive(
                    path,
                    uid=1000,
                    gid=2000,
                )

            ownership.assert_called_once_with(
                path,
                uid=1000,
                gid=2000,
            )

    def test_recursive_ownership_for_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "directory"
            child_directory = root / "nested"
            child_file = child_directory / "file.txt"

            child_directory.mkdir(parents=True)
            child_file.write_text(
                "content",
                encoding="utf-8",
            )

            with patch(f"{MODULE}._set_ownership") as ownership:
                set_ownership_recursive(
                    root,
                    uid=1000,
                    gid=2000,
                )

            self.assertEqual(
                ownership.call_args_list,
                [
                    call(
                        root,
                        uid=1000,
                        gid=2000,
                    ),
                    call(
                        child_directory,
                        uid=1000,
                        gid=2000,
                    ),
                    call(
                        child_file,
                        uid=1000,
                        gid=2000,
                    ),
                ],
            )

    def test_symlink_is_not_traversed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()

            link = root / "link"
            link.symlink_to(
                target,
                target_is_directory=True,
            )

            with patch(f"{MODULE}._set_ownership") as ownership:
                set_ownership_recursive(
                    link,
                    uid=1000,
                    gid=2000,
                )

            ownership.assert_called_once_with(
                link,
                uid=1000,
                gid=2000,
            )

    def test_rejects_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing"

            with self.assertRaisesRegex(
                FileNotFoundError,
                "Ownership target does not exist",
            ):
                set_ownership_recursive(
                    path,
                    uid=1000,
                    gid=2000,
                )


class InstallDirectoryTests(unittest.TestCase):
    def test_copies_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            destination = root / "destination"

            nested = source / "nested"
            nested.mkdir(parents=True)
            (source / "sound.wav").write_text(
                "sound",
                encoding="utf-8",
            )
            (nested / "note.txt").write_text(
                "note",
                encoding="utf-8",
            )

            with (
                patch(f"{MODULE}._set_ownership") as set_ownership,
                patch(f"{MODULE}.set_ownership_recursive") as recursive,
            ):
                install_directory(
                    source,
                    destination,
                    uid=1000,
                    gid=2000,
                )

            self.assertEqual(
                (destination / "sound.wav").read_text(encoding="utf-8"),
                "sound",
            )
            self.assertEqual(
                (destination / "nested" / "note.txt").read_text(encoding="utf-8"),
                "note",
            )

            set_ownership.assert_called_once_with(
                destination,
                uid=1000,
                gid=2000,
            )
            self.assertCountEqual(
                recursive.call_args_list,
                [
                    call(
                        destination / "sound.wav",
                        uid=1000,
                        gid=2000,
                    ),
                    call(
                        destination / "nested",
                        uid=1000,
                        gid=2000,
                    ),
                ],
            )

    def test_does_not_overwrite_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            destination = root / "destination"

            source.mkdir()
            destination.mkdir()

            source_file = source / "sound.wav"
            destination_file = destination / "sound.wav"

            source_file.write_text(
                "new",
                encoding="utf-8",
            )
            destination_file.write_text(
                "existing",
                encoding="utf-8",
            )

            with (
                patch(f"{MODULE}._set_ownership"),
                patch(f"{MODULE}.set_ownership_recursive") as ownership,
                patch(f"{MODULE}.shutil.copy2") as copy_file,
            ):
                install_directory(
                    source,
                    destination,
                    uid=1000,
                    gid=2000,
                )

            self.assertEqual(
                destination_file.read_text(encoding="utf-8"),
                "existing",
            )
            copy_file.assert_not_called()
            ownership.assert_called_once_with(
                destination_file,
                uid=1000,
                gid=2000,
            )

    def test_rejects_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "missing"
            destination = Path(temp_dir) / "destination"

            with self.assertRaisesRegex(
                FileNotFoundError,
                "Asset source directory does not exist",
            ):
                install_directory(
                    source,
                    destination,
                    uid=1000,
                    gid=2000,
                )

    def test_rejects_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            destination = Path(temp_dir) / "destination"
            source.write_text(
                "not a directory",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                FileNotFoundError,
                "Asset source directory does not exist",
            ):
                install_directory(
                    source,
                    destination,
                    uid=1000,
                    gid=2000,
                )

    def test_rejects_destination_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            destination = Path(temp_dir) / "destination"

            source.mkdir()
            destination.write_text(
                "not a directory",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                install_directory(
                    source,
                    destination,
                    uid=1000,
                    gid=2000,
                )

    def test_rejects_symbolic_link_in_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            destination = root / "destination"
            external = root / "external.txt"

            source.mkdir()
            external.write_text(
                "external",
                encoding="utf-8",
            )
            (source / "linked.txt").symlink_to(external)

            with (
                patch(f"{MODULE}._set_ownership"),
                self.assertRaisesRegex(
                    ValueError,
                    "Asset source contains a symbolic link",
                ),
            ):
                install_directory(
                    source,
                    destination,
                    uid=1000,
                    gid=2000,
                )


class PopulateMediaTests(unittest.TestCase):
    def test_installs_media_for_enabled_accounts(self) -> None:
        repository = Path("/opt/libs/betabox_robotics")
        first = make_account(
            username="student1",
            home=Path("/home/student1"),
        )
        second = make_account(
            username="student2",
            home=Path("/home/student2"),
            install_media=False,
        )

        with (
            patch(
                f"{MODULE}.group_id",
                return_value=2000,
            ) as shared_group,
            patch(
                f"{MODULE}.account_ids",
                return_value=(
                    1001,
                    1002,
                ),
            ) as ids,
            patch(f"{MODULE}.install_directory") as install,
        ):
            populate_media(
                repository,
                accounts=(
                    first,
                    second,
                ),
            )

        shared_group.assert_called_once_with(BETABOX_SHARED_GROUP)
        ids.assert_called_once_with("student1")
        install.assert_called_once_with(
            repository / "deployment" / "assets" / "sounds",
            Path("/home/student1/media/sounds"),
            uid=1001,
            gid=2000,
        )

    def test_accepts_generator(self) -> None:
        account = make_account()

        with (
            patch(
                f"{MODULE}.group_id",
                return_value=2000,
            ),
            patch(
                f"{MODULE}.account_ids",
                return_value=(
                    1000,
                    1001,
                ),
            ),
            patch(f"{MODULE}.install_directory") as install,
        ):
            populate_media(
                Path("/repository"),
                accounts=(value for value in (account,)),
            )

        install.assert_called_once()

    def test_rejects_non_iterable_accounts(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "accounts must be iterable",
        ):
            populate_media(
                Path("/repository"),
                accounts=123,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_account_entry(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "accounts must contain only ProvisionedAccount instances",
        ):
            populate_media(
                Path("/repository"),
                accounts=(
                    object(),  # type: ignore[arg-type]
                ),
            )


if __name__ == "__main__":
    unittest.main()
