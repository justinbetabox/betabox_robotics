from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from betabox_robotics.exceptions import (
    RobotBusyError,
)


ROBOT_LOCK_PATH = Path(
    "/tmp/betabox-robot.lock"
)


class RobotOwnership:
    """
    Cross-process exclusive ownership of robot hardware.
    """

    def __init__(
        self,
        *,
        owner: str = "Python application",
        lock_path: Path = ROBOT_LOCK_PATH,
    ) -> None:
        self.owner = owner
        self.lock_path = lock_path
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

        lock_file = self.lock_path.open(
            "a+",
            encoding="utf-8",
        )

        try:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX
                | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            details = self._read_owner(
                lock_file
            )

            lock_file.close()

            owner = details.get(
                "owner",
                "another application",
            )

            raise RobotBusyError(
                f"The robot is currently being used by {owner}. "
                "Close that application or finish its robot code, "
                "then try again."
            ) from None

        lock_file.seek(0)
        lock_file.truncate()

        json.dump(
            {
                "pid": os.getpid(),
                "owner": self.owner,
                "acquired_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            },
            lock_file,
        )

        lock_file.flush()
        os.fsync(
            lock_file.fileno()
        )

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

    def _read_owner(
        self,
        lock_file: IO[str],
    ) -> dict:
        try:
            lock_file.seek(0)
            value = json.load(
                lock_file
            )

            if isinstance(value, dict):
                return value

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            pass

        return {}

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.release()
