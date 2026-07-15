from __future__ import annotations

import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from queue import Empty

from betabox_robotics.exceptions import (
    RobotBusyError,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnership,
)


def hold_robot_lock(
    lock_path: str,
    ready_queue,
    release_event,
) -> None:
    ownership = RobotOwnership(
        owner="Test Child",
        lock_path=Path(lock_path),
    )

    try:
        ownership.acquire()
        ready_queue.put(("acquired", None))

        release_event.wait(
            timeout=10.0
        )
    except Exception as exc:
        ready_queue.put(
            (
                "error",
                repr(exc),
            )
        )
    finally:
        ownership.release()


class RobotOwnershipTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.lock_path = (
            Path(
                self.temporary_directory.name
            )
            / "robot.lock"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_acquire_and_release(self) -> None:
        ownership = RobotOwnership(
            owner="Unit Test",
            lock_path=self.lock_path,
        )

        self.assertFalse(
            ownership.acquired
        )

        ownership.acquire()

        self.assertTrue(
            ownership.acquired
        )

        ownership.release()

        self.assertFalse(
            ownership.acquired
        )

    def test_acquire_is_idempotent(self) -> None:
        ownership = RobotOwnership(
            owner="Unit Test",
            lock_path=self.lock_path,
        )

        ownership.acquire()
        ownership.acquire()

        self.assertTrue(
            ownership.acquired
        )

        ownership.release()

    def test_release_is_idempotent(self) -> None:
        ownership = RobotOwnership(
            owner="Unit Test",
            lock_path=self.lock_path,
        )

        ownership.release()

        self.assertFalse(
            ownership.acquired
        )

        ownership.acquire()
        ownership.release()
        ownership.release()

        self.assertFalse(
            ownership.acquired
        )

    def test_context_manager_releases_lock(
        self,
    ) -> None:
        with RobotOwnership(
            owner="Context Test",
            lock_path=self.lock_path,
        ) as ownership:
            self.assertTrue(
                ownership.acquired
            )

        replacement = RobotOwnership(
            owner="Replacement",
            lock_path=self.lock_path,
        )

        replacement.acquire()

        self.assertTrue(
            replacement.acquired
        )

        replacement.release()

    def test_context_manager_releases_after_exception(
        self,
    ) -> None:
        with self.assertRaises(
            RuntimeError
        ):
            with RobotOwnership(
                owner="Context Test",
                lock_path=self.lock_path,
            ):
                raise RuntimeError(
                    "expected test failure"
                )

        replacement = RobotOwnership(
            owner="Replacement",
            lock_path=self.lock_path,
        )

        replacement.acquire()
        replacement.release()

    def test_writes_owner_metadata(self) -> None:
        ownership = RobotOwnership(
            owner="Metadata Test",
            lock_path=self.lock_path,
        )

        ownership.acquire()

        metadata = json.loads(
            self.lock_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            metadata["owner"],
            "Metadata Test",
        )

        self.assertIsInstance(
            metadata["pid"],
            int,
        )

        self.assertIn(
            "acquired_at",
            metadata,
        )

        ownership.release()

    def test_stale_metadata_does_not_block_lock(
        self,
    ) -> None:
        self.lock_path.write_text(
            json.dumps(
                {
                    "pid": 999999,
                    "owner": "Stale Owner",
                    "acquired_at": (
                        "2000-01-01T00:00:00+00:00"
                    ),
                }
            ),
            encoding="utf-8",
        )

        ownership = RobotOwnership(
            owner="Current Owner",
            lock_path=self.lock_path,
        )

        ownership.acquire()

        self.assertTrue(
            ownership.acquired
        )

        ownership.release()

    def test_competing_process_receives_busy_error(
        self,
    ) -> None:
        context = (
            multiprocessing.get_context(
                "spawn"
            )
        )

        ready_queue = context.Queue()
        release_event = context.Event()

        process = context.Process(
            target=hold_robot_lock,
            args=(
                str(self.lock_path),
                ready_queue,
                release_event,
            ),
        )

        process.start()

        try:
            try:
                state, message = (
                    ready_queue.get(
                        timeout=5.0
                    )
                )
            except Empty as exc:
                self.fail(
                    "Child process did not acquire "
                    "the robot lock"
                )
                raise exc

            self.assertEqual(
                state,
                "acquired",
                message,
            )

            competing = RobotOwnership(
                owner="Parent Test",
                lock_path=self.lock_path,
            )

            with self.assertRaisesRegex(
                RobotBusyError,
                "Test Child",
            ):
                competing.acquire()

            self.assertFalse(
                competing.acquired
            )

        finally:
            release_event.set()
            process.join(
                timeout=5.0
            )

            if process.is_alive():
                process.terminate()
                process.join(
                    timeout=2.0
                )

        self.assertEqual(
            process.exitcode,
            0,
        )

        replacement = RobotOwnership(
            owner="Replacement",
            lock_path=self.lock_path,
        )

        replacement.acquire()
        replacement.release()


if __name__ == "__main__":
    unittest.main()
