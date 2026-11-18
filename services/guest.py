from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from betabox_robotics.services.accounts import (
    ProvisionedAccount,
    account_by_username,
)
from betabox_robotics.services.privileges import (
    require_root_or_elevate,
)
from betabox_robotics.services.workspace import (
    account_ids,
    create_workspace,
    populate_media,
)

DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


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


@dataclass(frozen=True, slots=True)
class GuestWorkspaceStatus:
    """Current state of the Guest workspace."""

    account_exists: bool
    home_exists: bool
    curriculum_exists: bool
    media_exists: bool
    preferences_exist: bool

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "account_exists",
            "home_exists",
            "curriculum_exists",
            "media_exists",
            "preferences_exist",
        ):
            if not isinstance(
                getattr(self, name),
                bool,
            ):
                raise TypeError(f"{name} must be a boolean")

    @property
    def ok(self) -> bool:
        return all(
            (
                self.account_exists,
                self.home_exists,
                self.curriculum_exists,
                self.media_exists,
                self.preferences_exist,
            )
        )


def guest_account() -> ProvisionedAccount:
    """Return the managed Guest account."""

    return account_by_username("guest")


def require_root() -> None:
    """Require root privileges for Guest modification."""

    if os.geteuid() != 0:
        raise PermissionError("Guest workspace management requires root.")


def provision_guest(
    *,
    repository_root: str | Path = DEFAULT_REPOSITORY_ROOT,
) -> None:
    repository_root_value = _validate_path(
        repository_root,
        name="repository_root",
    )

    require_root()

    account = guest_account()

    create_workspace(account)

    if account.install_media:
        populate_media(
            repository_root_value,
            accounts=(account,),
        )


def _reject_guest_mounts(home: Path) -> None:
    """Refuse to reset Guest when mounts exist inside its home."""

    try:
        mountinfo = Path("/proc/self/mountinfo").read_text(
            encoding="utf-8",
        )
    except OSError as exc:
        raise RuntimeError("Cannot verify Guest filesystem mounts.") from exc

    for line in mountinfo.splitlines():
        fields = line.split(" - ", 1)[0].split()

        if len(fields) < 5:
            raise RuntimeError("Invalid filesystem mount information.")

        mountpoint = re.sub(
            r"\\([0-7]{3})",
            lambda match: chr(int(match.group(1), 8)),
            fields[4],
        )

        mounted_path = Path(mountpoint)

        if mounted_path == home or home in mounted_path.parents:
            raise RuntimeError(
                f"Refusing Guest reset: mounted filesystem found at {mounted_path}"
            )


def _mount_id(fd: int) -> int:
    """Read the Linux mount ID of an open file descriptor."""

    info = Path(f"/proc/self/fdinfo/{fd}").read_text(
        encoding="ascii",
    )

    for line in info.splitlines():
        key, separator, value = line.partition(":")

        if separator and key == "mnt_id":
            try:
                return int(value.strip())
            except ValueError as exc:
                raise RuntimeError("Invalid mount ID") from exc

    raise RuntimeError("Cannot determine mount ID")


def _clear_guest_contents(home: Path) -> None:
    """Delete Guest contents without following symlinks or crossing mounts."""

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC

    home_fd = os.open(home, flags)
    frames = []

    try:
        opened = os.fstat(home_fd)
        current = os.stat(home, follow_symlinks=False)

        if (
            opened.st_dev,
            opened.st_ino,
        ) != (
            current.st_dev,
            current.st_ino,
        ):
            raise RuntimeError("Guest home changed during reset.")

        home_mount_id = _mount_id(home_fd)

        frames.append(
            (
                home_fd,
                None,
                None,
                None,
                iter(os.listdir(home_fd)),
            )
        )

        while frames:
            fd, parent_fd, dirname, identity, entries = frames[-1]

            try:
                name = next(entries)

            except StopIteration:
                if parent_fd is None:
                    break

                current = os.stat(
                    dirname,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )

                if (
                    current.st_dev,
                    current.st_ino,
                ) != identity:
                    raise RuntimeError("Guest directory changed during reset.")

                frames.pop()
                os.close(fd)

                os.rmdir(
                    dirname,
                    dir_fd=parent_fd,
                )

                continue

            entry = os.stat(
                name,
                dir_fd=fd,
                follow_symlinks=False,
            )

            if not stat.S_ISDIR(entry.st_mode):
                os.unlink(name, dir_fd=fd)
                continue

            child_fd = os.open(
                name,
                flags,
                dir_fd=fd,
            )

            try:
                child = os.fstat(child_fd)

                child_identity = (
                    child.st_dev,
                    child.st_ino,
                )

                if child_identity != (
                    entry.st_dev,
                    entry.st_ino,
                ):
                    raise RuntimeError("Guest directory changed during reset.")

                if _mount_id(child_fd) != home_mount_id:
                    raise RuntimeError("Refusing Guest reset: nested mount detected.")

                child_entries = iter(os.listdir(child_fd))

            except BaseException:
                os.close(child_fd)
                raise

            frames.append(
                (
                    child_fd,
                    fd,
                    name,
                    child_identity,
                    child_entries,
                )
            )

    finally:
        for fd, *_ in reversed(frames):
            os.close(fd)


def _reject_active_guest_processes() -> None:
    """Refuse Guest reset while any Guest-owned process is running."""

    guest_uid, _ = account_ids("guest")

    try:
        processes = tuple(Path("/proc").iterdir())
    except OSError as exc:
        raise RuntimeError("Cannot inspect running Guest processes.") from exc

    for process in processes:
        if not process.name.isdecimal():
            continue

        try:
            status = (process / "status").read_text(
                encoding="utf-8",
            )
        except FileNotFoundError:
            # Process exited during inspection.
            continue
        except OSError as exc:
            raise RuntimeError(f"Cannot inspect process {process.name}.") from exc

        uid_line = next(
            (line for line in status.splitlines() if line.startswith("Uid:")),
            None,
        )

        if uid_line is None:
            raise RuntimeError(f"Cannot determine process {process.name} ownership.")

        try:
            process_uids = tuple(int(value) for value in uid_line.split()[1:])
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid UID information for process {process.name}."
            ) from exc

        if len(process_uids) != 4:
            raise RuntimeError(
                f"Incomplete UID information for process {process.name}."
            )

        if guest_uid in process_uids:
            raise RuntimeError(
                f"Refusing Guest reset: active Guest process PID {process.name}."
            )


def reset_guest(
    *,
    repository_root: str | Path = DEFAULT_REPOSITORY_ROOT,
) -> None:
    """Reset the temporary Guest workspace."""
    repository_root_value = _validate_path(
        repository_root,
        name="repository_root",
    )
    require_root()

    account = guest_account()

    if account.persistent:
        raise RuntimeError("Refusing to reset a persistent account.")

    expected_home = Path("/home") / account.username

    if account.home != expected_home:
        raise RuntimeError(f"Refusing to reset unexpected path: {account.home}")

    if not account.home.is_dir():
        raise RuntimeError(f"Guest home directory does not exist: {account.home}")

    if account.home.is_symlink():
        raise RuntimeError("Refusing to reset a symlinked Guest home.")

    _reject_guest_mounts(account.home)
    _reject_active_guest_processes()
    _clear_guest_contents(account.home)

    provision_guest(
        repository_root=repository_root_value,
    )


def guest_status() -> GuestWorkspaceStatus:
    try:
        account = guest_account()
        _ = account_ids(account.username)

        return GuestWorkspaceStatus(
            account_exists=True,
            home_exists=(account.home.is_dir()),
            curriculum_exists=(account.home / "curriculum").is_dir(),
            media_exists=(account.home / "media").is_dir(),
            preferences_exist=(
                account.home / ".config" / "betabox" / "preferences"
            ).is_dir(),
        )

    except (
        LookupError,
        RuntimeError,
        OSError,
    ):
        return GuestWorkspaceStatus(
            account_exists=False,
            home_exists=False,
            curriculum_exists=False,
            media_exists=False,
            preferences_exist=False,
        )


def print_status(
    status: GuestWorkspaceStatus,
) -> None:
    print(f"Account:      {'OK' if status.account_exists else 'Missing'}")
    print(f"Home:         {'OK' if status.home_exists else 'Missing'}")
    print(f"Curriculum:   {'OK' if status.curriculum_exists else 'Missing'}")
    print(f"Media:        {'OK' if status.media_exists else 'Missing'}")
    print(f"Preferences:  {'OK' if status.preferences_exist else 'Missing'}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="betabox guest",
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    _ = subparsers.add_parser(
        "status",
        help="Show Guest workspace status",
    )
    _ = subparsers.add_parser(
        "provision",
        help="Create the Guest workspace",
    )
    _ = subparsers.add_parser(
        "reset",
        help="Reset the Guest workspace",
    )

    return parser


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    command = cast(
        object,
        args.command,
    )

    if command is not None and not isinstance(
        command,
        str,
    ):
        raise TypeError("command must be a string")

    try:
        if command == "status":
            status = guest_status()
            print_status(status)
            return 0 if status.ok else 1

        if command == "provision":
            require_root_or_elevate(
                [
                    "guest",
                    "provision",
                ]
            )
            provision_guest()
            print("Guest workspace provisioned.")
            return 0

        if command == "reset":
            require_root_or_elevate(
                [
                    "guest",
                    "reset",
                ]
            )
            reset_guest()
            print("Guest workspace reset.")
            return 0

    except (
        LookupError,
        PermissionError,
        RuntimeError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            f"Guest workspace operation failed: {exc}",
            file=sys.stderr,
        )
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
