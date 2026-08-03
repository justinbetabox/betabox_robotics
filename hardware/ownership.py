from __future__ import annotations

import fcntl
import grp
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Self

from betabox_robotics.exceptions import (
    RobotBusyError,
)

ROBOT_LOCK_PATH = Path("/tmp/betabox-robot.lock")
ROBOT_LOCK_GROUP = "betabox"
ROBOT_LOCK_MODE = 0o660


def _open_robot_lock(
    lock_path: Path,
) -> IO[str]:
    """Open or safely create the shared robot lock."""

    try:
        group = grp.getgrnam(ROBOT_LOCK_GROUP)
    except KeyError as exc:
        raise RuntimeError(
            f"Required Linux group does not exist: {ROBOT_LOCK_GROUP}"
        ) from exc

    base_flags = os.O_RDWR | os.O_CLOEXEC

    if hasattr(
        os,
        "O_NOFOLLOW",
    ):
        base_flags |= os.O_NOFOLLOW

    created = False

    try:
        fd = os.open(
            lock_path,
            base_flags,
        )
    except FileNotFoundError:
        try:
            fd = os.open(
                lock_path,
                (base_flags | os.O_CREAT | os.O_EXCL),
                ROBOT_LOCK_MODE,
            )
            created = True

        except FileExistsError:
            fd = os.open(
                lock_path,
                base_flags,
            )

    try:
        if created:
            os.fchown(
                fd,
                -1,
                group.gr_gid,
            )
            os.fchmod(
                fd,
                ROBOT_LOCK_MODE,
            )

        return os.fdopen(
            fd,
            "r+",
            encoding="utf-8",
        )

    except BaseException:
        os.close(fd)
        raise


@dataclass(frozen=True, slots=True)
class RobotOwnershipStatus:
    available: bool
    owner: str | None
    pid: int | None
    acquired_at: str | None
    error: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "available": self.available,
            "owner": self.owner,
            "pid": self.pid,
            "acquired_at": self.acquired_at,
            "error": self.error,
        }


class RobotOwnership:
    """Cross-process exclusive ownership of robot hardware."""

    def __init__(
        self,
        *,
        owner: str = "Python application",
        lock_path: Path = ROBOT_LOCK_PATH,
    ) -> None:
        normalized_owner = owner.strip()

        if not normalized_owner:
            raise ValueError("owner cannot be empty")

        self.owner = normalized_owner
        self.lock_path = Path(lock_path)
        self._file: IO[str] | None = None

    @property
    def acquired(self) -> bool:
        return self._file is not None

    def acquire(self) -> None:
        if self._file is not None:
            return

        self.lock_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        lock_file = _open_robot_lock(self.lock_path)

        try:
            fcntl.flock(
                lock_file.fileno(),
                (fcntl.LOCK_EX | fcntl.LOCK_NB),
            )

        except BlockingIOError:
            details = _read_lock_metadata(lock_file)
            lock_file.close()

            owner = _optional_string(details.get("owner")) or "another application"

            raise RobotBusyError(
                "The robot is currently being used by "
                f"{owner}. Close that application or "
                "finish its robot code, then try again."
            ) from None

        try:
            lock_file.seek(0)
            lock_file.truncate()

            json.dump(
                {
                    "pid": os.getpid(),
                    "owner": self.owner,
                    "acquired_at": (datetime.now(UTC).isoformat()),
                },
                lock_file,
            )

            lock_file.flush()
            os.fsync(lock_file.fileno())

        except BaseException:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_UN,
                )
            finally:
                lock_file.close()

            raise

        self._file = lock_file

    def release(self) -> None:
        lock_file = self._file

        if lock_file is None:
            return

        self._file = None

        try:
            lock_file.seek(0)
            lock_file.truncate()
            lock_file.flush()

            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_UN,
            )

        finally:
            lock_file.close()

    def __enter__(
        self,
    ) -> Self:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.release()


def probe_robot_ownership(
    lock_path: Path = ROBOT_LOCK_PATH,
) -> RobotOwnershipStatus:
    try:
        lock_file = _open_robot_lock(Path(lock_path))

    except (
        OSError,
        RuntimeError,
    ) as exc:
        return RobotOwnershipStatus(
            available=False,
            owner=None,
            pid=None,
            acquired_at=None,
            error=str(exc),
        )

    acquired = False

    try:
        try:
            fcntl.flock(
                lock_file.fileno(),
                (fcntl.LOCK_EX | fcntl.LOCK_NB),
            )
            acquired = True

        except BlockingIOError:
            details = _read_lock_metadata(lock_file)

            return RobotOwnershipStatus(
                available=False,
                owner=_optional_string(details.get("owner")),
                pid=_optional_int(details.get("pid")),
                acquired_at=_optional_string(details.get("acquired_at")),
            )

        return RobotOwnershipStatus(
            available=True,
            owner=None,
            pid=None,
            acquired_at=None,
        )

    finally:
        if acquired:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_UN,
                )
            except OSError:
                pass

        lock_file.close()


def _read_lock_metadata(
    lock_file: IO[str],
) -> dict[str, object]:
    try:
        lock_file.seek(0)
        value = json.load(lock_file)

        if isinstance(
            value,
            dict,
        ):
            return value

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
    ):
        pass

    return {}


def _optional_string(
    value: object,
) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(
    value: object,
) -> int | None:
    if isinstance(value, bool):
        return None

    return value if isinstance(value, int) else None
