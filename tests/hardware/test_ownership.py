from __future__ import annotations

import fcntl
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from queue import Empty
from unittest.mock import MagicMock, patch

from betabox_robotics.exceptions import (
    RobotBusyError,
)
from betabox_robotics.hardware.ownership import (
    RobotOwnership,
    probe_robot_ownership,
)


def hold_robot_lock(
    lock_path: str,
    ready_queue,
    release_event,
) -> None:
    """
    Acquire a robot lock in a child process and hold it until released.

    This helper must remain at module scope so it can be used with the
    multiprocessing "spawn" start method.
    """

    ownership = RobotOwnership(
        owner="Test Child",
        lock_path=Path(lock_path),
    )

    try:
        ownership.acquire()

        ready_queue.put(
            (
                "acquired",
                None,
            )
        )

        release_event.wait(
            timeout=10.0,
        )

    except Exception as exc:  # noqa: BLE001
        ready_queue.put(
            (
                "error",
                repr(exc),
            )
        )

    finally:
        ownership.release()


class RobotOwnershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()

        self.lock_path = Path(self.temporary_directory.name) / "robot.lock"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def start_lock_holder(
        self,
    ):
        """Start a child process that owns the test robot lock."""

        context = multiprocessing.get_context("spawn")

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
            state, message = ready_queue.get(
                timeout=5.0,
            )
        except Empty:
            release_event.set()

            process.terminate()
            process.join(
                timeout=2.0,
            )

            self.fail("Child process did not acquire the robot lock")

        self.assertEqual(
            state,
            "acquired",
            message,
        )

        return (
            process,
            release_event,
        )

    def stop_lock_holder(
        self,
        process,
        release_event,
    ) -> None:
        """Release and stop a child lock-holder process."""

        release_event.set()

        process.join(
            timeout=5.0,
        )

        if process.is_alive():
            process.terminate()
            process.join(
                timeout=2.0,
            )

        self.assertEqual(
            process.exitcode,
            0,
        )

    def test_empty_owner_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "owner cannot be empty",
        ):
            RobotOwnership(
                owner="   ",
                lock_path=self.lock_path,
            )

    def test_owner_is_stripped(
        self,
    ) -> None:
        ownership = RobotOwnership(
            owner="  Unit Test  ",
            lock_path=self.lock_path,
        )

        self.assertEqual(
            ownership.owner,
            "Unit Test",
        )

    def test_acquire_and_release(
        self,
    ) -> None:
        ownership = RobotOwnership(
            owner="Unit Test",
            lock_path=self.lock_path,
        )

        self.assertFalse(ownership.acquired)

        ownership.acquire()

        self.assertTrue(ownership.acquired)

        ownership.release()

        self.assertFalse(ownership.acquired)

    def test_acquire_is_idempotent(
        self,
    ) -> None:
        ownership = RobotOwnership(
            owner="Unit Test",
            lock_path=self.lock_path,
        )

        ownership.acquire()
        ownership.acquire()

        self.assertTrue(ownership.acquired)

        ownership.release()

    def test_release_is_idempotent(
        self,
    ) -> None:
        ownership = RobotOwnership(
            owner="Unit Test",
            lock_path=self.lock_path,
        )

        ownership.release()

        self.assertFalse(ownership.acquired)

        ownership.acquire()
        ownership.release()
        ownership.release()

        self.assertFalse(ownership.acquired)

    def test_context_manager_returns_self(
        self,
    ) -> None:
        ownership = RobotOwnership(
            owner="Context Test",
            lock_path=self.lock_path,
        )

        with ownership as entered:
            self.assertIs(
                entered,
                ownership,
            )
            self.assertTrue(ownership.acquired)

        self.assertFalse(ownership.acquired)

    def test_context_manager_releases_lock(
        self,
    ) -> None:
        with RobotOwnership(
            owner="Context Test",
            lock_path=self.lock_path,
        ) as ownership:
            self.assertTrue(ownership.acquired)

        replacement = RobotOwnership(
            owner="Replacement",
            lock_path=self.lock_path,
        )

        replacement.acquire()

        self.assertTrue(replacement.acquired)

        replacement.release()

    def test_context_manager_releases_after_exception(
        self,
    ) -> None:
        with (
            self.assertRaisesRegex(
                RuntimeError,
                "expected test failure",
            ),
            RobotOwnership(
                owner="Context Test",
                lock_path=self.lock_path,
            ),
        ):
            raise RuntimeError("expected test failure")

        replacement = RobotOwnership(
            owner="Replacement",
            lock_path=self.lock_path,
        )

        replacement.acquire()
        replacement.release()

    def test_writes_owner_metadata(
        self,
    ) -> None:
        ownership = RobotOwnership(
            owner="Metadata Test",
            lock_path=self.lock_path,
        )

        ownership.acquire()

        try:
            metadata = json.loads(
                self.lock_path.read_text(
                    encoding="utf-8",
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

            self.assertNotIsInstance(
                metadata["pid"],
                bool,
            )

            self.assertIsInstance(
                metadata["acquired_at"],
                str,
            )

            self.assertTrue(metadata["acquired_at"])

        finally:
            ownership.release()

    def test_release_clears_metadata(
        self,
    ) -> None:
        ownership = RobotOwnership(
            owner="Metadata Test",
            lock_path=self.lock_path,
        )

        ownership.acquire()
        ownership.release()

        self.assertEqual(
            self.lock_path.read_text(
                encoding="utf-8",
            ),
            "",
        )

    def test_stale_metadata_does_not_block_lock(
        self,
    ) -> None:
        self.lock_path.write_text(
            json.dumps(
                {
                    "pid": 999999,
                    "owner": "Stale Owner",
                    "acquired_at": ("2000-01-01T00:00:00+00:00"),
                }
            ),
            encoding="utf-8",
        )

        ownership = RobotOwnership(
            owner="Current Owner",
            lock_path=self.lock_path,
        )

        ownership.acquire()

        self.assertTrue(ownership.acquired)

        ownership.release()

    def test_metadata_write_failure_releases_lock(
        self,
    ) -> None:
        lock_file = MagicMock()
        lock_file.fileno.return_value = 42
        lock_file.flush.side_effect = OSError("flush failed")

        ownership = RobotOwnership(
            owner="Failure Test",
            lock_path=self.lock_path,
        )

        with (
            patch(
                "betabox_robotics.hardware.ownership._open_robot_lock",
                return_value=lock_file,
            ),
            patch("betabox_robotics.hardware.ownership.fcntl.flock") as flock,
            self.assertRaisesRegex(
                OSError,
                "flush failed",
            ),
        ):
            ownership.acquire()

        self.assertFalse(ownership.acquired)

        flock.assert_any_call(
            42,
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )

        flock.assert_any_call(
            42,
            fcntl.LOCK_UN,
        )

        self.assertEqual(
            flock.call_count,
            2,
        )

        lock_file.close.assert_called_once_with()

    def test_competing_process_receives_busy_error(
        self,
    ) -> None:
        process, release_event = self.start_lock_holder()

        try:
            competing = RobotOwnership(
                owner="Parent Test",
                lock_path=self.lock_path,
            )

            with self.assertRaisesRegex(
                RobotBusyError,
                "Test Child",
            ):
                competing.acquire()

            self.assertFalse(competing.acquired)

        finally:
            self.stop_lock_holder(
                process,
                release_event,
            )

        replacement = RobotOwnership(
            owner="Replacement",
            lock_path=self.lock_path,
        )

        replacement.acquire()
        replacement.release()

    def test_malformed_owner_metadata_uses_fallback(
        self,
    ) -> None:
        process, release_event = self.start_lock_holder()

        try:
            # The child still holds the real flock, but the informational
            # metadata is deliberately replaced with malformed content.
            self.lock_path.write_text(
                '{"owner": null}',
                encoding="utf-8",
            )

            competing = RobotOwnership(
                owner="Parent Test",
                lock_path=self.lock_path,
            )

            with self.assertRaisesRegex(
                RobotBusyError,
                "another application",
            ):
                competing.acquire()

            self.assertFalse(competing.acquired)

        finally:
            self.stop_lock_holder(
                process,
                release_event,
            )

    def test_probe_reports_available_robot(
        self,
    ) -> None:
        status = probe_robot_ownership(self.lock_path)

        self.assertTrue(status.available)

        self.assertIsNone(status.owner)

        self.assertIsNone(status.pid)

        self.assertIsNone(status.acquired_at)

        self.assertIsNone(status.error)

    def test_probe_does_not_retain_available_lock(
        self,
    ) -> None:
        status = probe_robot_ownership(self.lock_path)

        self.assertTrue(status.available)

        ownership = RobotOwnership(
            owner="After Probe",
            lock_path=self.lock_path,
        )

        ownership.acquire()

        self.assertTrue(ownership.acquired)

        ownership.release()

    def test_probe_reports_current_owner(
        self,
    ) -> None:
        process, release_event = self.start_lock_holder()

        try:
            status = probe_robot_ownership(self.lock_path)

            self.assertFalse(status.available)

            self.assertEqual(
                status.owner,
                "Test Child",
            )

            self.assertIsInstance(
                status.pid,
                int,
            )

            self.assertNotIsInstance(
                status.pid,
                bool,
            )

            self.assertIsInstance(
                status.acquired_at,
                str,
            )

            self.assertTrue(status.acquired_at)

            self.assertIsNone(status.error)

        finally:
            self.stop_lock_holder(
                process,
                release_event,
            )

    def test_probe_returns_open_error(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.hardware.ownership._open_robot_lock",
            side_effect=OSError("cannot open lock"),
        ):
            status = probe_robot_ownership(self.lock_path)

        self.assertFalse(status.available)

        self.assertIsNone(status.owner)

        self.assertIsNone(status.pid)

        self.assertIsNone(status.acquired_at)

        self.assertEqual(
            status.error,
            "cannot open lock",
        )

    def test_probe_returns_missing_group_error(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.hardware.ownership._open_robot_lock",
            side_effect=RuntimeError("Required Linux group does not exist: betabox"),
        ):
            status = probe_robot_ownership(self.lock_path)

        self.assertFalse(status.available)

        self.assertEqual(
            status.error,
            "Required Linux group does not exist: betabox",
        )

    def test_probe_tolerates_invalid_json_metadata(
        self,
    ) -> None:
        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        with (
            patch(
                "betabox_robotics.hardware.ownership._open_robot_lock",
                return_value=lock_file,
            ),
            patch(
                "betabox_robotics.hardware.ownership.fcntl.flock",
                side_effect=BlockingIOError,
            ),
            patch(
                "betabox_robotics.hardware.ownership.json.load",
                side_effect=json.JSONDecodeError(
                    "bad JSON",
                    "",
                    0,
                ),
            ),
        ):
            status = probe_robot_ownership(self.lock_path)

        self.assertFalse(status.available)

        self.assertIsNone(status.owner)

        self.assertIsNone(status.pid)

        self.assertIsNone(status.acquired_at)

        self.assertIsNone(status.error)

        lock_file.close.assert_called_once_with()

    def test_probe_rejects_boolean_pid_metadata(
        self,
    ) -> None:
        lock_file = MagicMock()
        lock_file.fileno.return_value = 42

        with (
            patch(
                "betabox_robotics.hardware.ownership._open_robot_lock",
                return_value=lock_file,
            ),
            patch(
                "betabox_robotics.hardware.ownership.fcntl.flock",
                side_effect=BlockingIOError,
            ),
            patch(
                "betabox_robotics.hardware.ownership.json.load",
                return_value={
                    "owner": "Test Owner",
                    "pid": True,
                    "acquired_at": ("2026-08-03T12:00:00+00:00"),
                },
            ),
        ):
            status = probe_robot_ownership(self.lock_path)

        self.assertFalse(status.available)

        self.assertEqual(
            status.owner,
            "Test Owner",
        )

        self.assertIsNone(status.pid)

        self.assertEqual(
            status.acquired_at,
            "2026-08-03T12:00:00+00:00",
        )

        lock_file.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
