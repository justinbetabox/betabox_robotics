from __future__ import annotations

import pwd
from pathlib import Path

from .models import CheckResult
from .validation import (
    validate_optional_string,
    validate_path,
    validate_string,
)


def check_media_root(
    name: str,
    media_root: str | Path,
    *,
    success_message: str | None = None,
) -> CheckResult:
    """
    Verify that a Betabox media directory contains all
    required directories and bundled media files.
    """

    name_value = validate_string(
        name,
        name="name",
    )
    media_root_value = validate_path(
        media_root,
        name="media_root",
    )
    success_message_value = validate_optional_string(
        success_message,
        name="success_message",
    )

    required_paths = (
        media_root_value / "pictures",
        media_root_value / "videos",
        media_root_value / "sounds",
        media_root_value / "sounds" / "car-honk.mp3",
    )

    problems: list[str] = []

    for path in required_paths:
        try:
            exists = path.exists()
        except PermissionError:
            problems.append(f"{path}: permission denied")
            continue
        except OSError as exc:
            problems.append(f"{path}: {exc}")
            continue

        if not exists:
            problems.append(f"{path}: missing")

    if problems:
        return CheckResult(
            name=name_value,
            ok=False,
            message="; ".join(problems),
        )

    return CheckResult(
        name=name_value,
        ok=True,
        message=(
            success_message_value
            if success_message_value is not None
            else str(media_root_value)
        ),
    )


def check_runtime_media(
    username: str,
) -> CheckResult:
    """
    Verify the runtime media tree belonging to the
    Betabox service account.
    """

    username_value = validate_string(
        username,
        name="username",
    )
    check_name = f"runtime-media:{username_value}"

    try:
        user = pwd.getpwnam(username_value)
    except KeyError:
        return CheckResult(
            name=check_name,
            ok=False,
            message="service user does not exist",
        )
    except OSError as exc:
        return CheckResult(
            name=check_name,
            ok=False,
            message=str(exc),
        )

    media_root = Path(user.pw_dir) / "media"

    return check_media_root(
        check_name,
        media_root,
    )


def check_account_workspace(
    username: str,
    home: str | Path,
) -> CheckResult:
    """
    Verify the media tree within a managed account
    workspace.
    """

    username_value = validate_string(
        username,
        name="username",
    )
    home_value = validate_path(
        home,
        name="home",
    )

    return check_media_root(
        f"workspace:{username_value}",
        home_value / "media",
        success_message=str(home_value),
    )
