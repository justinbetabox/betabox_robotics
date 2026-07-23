from __future__ import annotations

import os
import pwd
import subprocess
from pathlib import Path


def run_command(*command: str) -> None:
    """Run a system command."""

    subprocess.run(
        command,
        check=True,
    )


def account_ids(
    username: str,
) -> tuple[int, int]:
    """Return the UID and primary GID for an account."""

    try:
        account = pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(
            f"Linux account does not exist: "
            f"{username}"
        ) from exc

    return account.pw_uid, account.pw_gid


def set_ownership_recursive(
    path: Path,
    *,
    uid: int,
    gid: int,
) -> None:
    """Set ownership on a path and its contents."""

    os.chown(
        path,
        uid,
        gid,
    )

    if not path.is_dir():
        return

    for child in path.rglob("*"):
        os.chown(
            child,
            uid,
            gid,
        )
