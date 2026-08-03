#!/usr/bin/env python3
"""
Betabox robot ownership developer demo.

Demonstrates the cross-process robot hardware lock used to prevent
multiple applications from controlling the robot at the same time.

This demo:

- probes the current ownership state;
- acquires the robot lock;
- displays the recorded ownership metadata;
- verifies that a competing process receives RobotBusyError;
- releases the lock;
- confirms that the robot becomes available again.

It does not open GPIO, I²C, motors, servos, or other physical hardware.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from queue import Empty

from betabox_robotics.exceptions import RobotBusyError
from betabox_robotics.hardware.ownership import (
    ROBOT_LOCK_PATH,
    RobotOwnership,
    RobotOwnershipStatus,
    probe_robot_ownership,
)


def print_status(
    heading: str,
    status: RobotOwnershipStatus,
) -> None:
    print()
    print(heading)
    print("-" * len(heading))
    print(f"Available:   {status.available}")
    print(f"Owner:       {status.owner or '-'}")
    print(f"PID:         {status.pid if status.pid is not None else '-'}")
    print(f"Acquired at: {status.acquired_at or '-'}")
    print(f"Error:       {status.error or '-'}")


def competing_process(
    lock_path: str,
    result_queue,
) -> None:
    """
    Attempt to acquire an already-held robot lock.

    The process sends its result back through result_queue.
    """

    ownership = RobotOwnership(
        owner="Ownership Demo Competitor",
        lock_path=Path(lock_path),
    )

    try:
        ownership.acquire()

    except RobotBusyError as exc:
        result_queue.put(
            (
                "busy",
                str(exc),
            )
        )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        result_queue.put(
            (
                "error",
                f"{type(exc).__name__}: {exc}",
            )
        )

    else:
        result_queue.put(
            (
                "acquired",
                "Competing process unexpectedly acquired the lock.",
            )
        )

    finally:
        ownership.release()


def verify_competing_process_is_blocked(
    lock_path: Path,
) -> bool:
    context = multiprocessing.get_context("spawn")

    result_queue = context.Queue()

    process = context.Process(
        target=competing_process,
        args=(
            str(lock_path),
            result_queue,
        ),
    )

    process.start()

    try:
        try:
            state, message = result_queue.get(timeout=5.0)

        except Empty:
            print("Competing process did not report a result within five seconds.")
            return False

    finally:
        process.join(timeout=5.0)

        if process.is_alive():
            print("Competing process did not exit normally; terminating it.")

            process.terminate()
            process.join(timeout=2.0)

    print()
    print("Competing process")
    print("-----------------")
    print(f"Result:  {state}")
    print(f"Message: {message}")
    print(f"Exit:    {process.exitcode}")

    return state == "busy" and process.exitcode == 0


def main() -> int:
    print()
    print("Betabox robot ownership demo")
    print("============================")
    print()
    print(f"Lock file: {ROBOT_LOCK_PATH}")
    print(
        "This demo uses only the shared ownership lock. "
        "It does not initialize robot hardware."
    )

    initial_status = probe_robot_ownership()

    print_status(
        "Initial ownership state",
        initial_status,
    )

    if not initial_status.available:
        print()
        print(
            "The robot lock is already held or unavailable. "
            "Close the current robot application before running "
            "this demo."
        )
        return 1

    ownership = RobotOwnership(owner="Ownership Developer Demo")

    try:
        print()
        print("Acquiring robot ownership...")

        ownership.acquire()

        print(f"Acquired: {ownership.acquired}")

        held_status = probe_robot_ownership()

        print_status(
            "Ownership state while held",
            held_status,
        )

        if held_status.available:
            print()
            print(
                "ERROR: Ownership probe reported the robot as "
                "available while this process held the lock."
            )
            return 1

        print()
        print(
            "Starting a competing process to confirm that "
            "the lock prevents concurrent ownership..."
        )

        if not verify_competing_process_is_blocked(ownership.lock_path):
            print()
            print("ERROR: The competing-process ownership check failed.")
            return 1

    except RobotBusyError as exc:
        print()
        print(f"Robot ownership unavailable: {exc}")
        return 1

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print()
        print(f"Ownership demo failed: {type(exc).__name__}: {exc}")
        return 1

    finally:
        print()
        print("Releasing robot ownership...")

        ownership.release()

        print(f"Acquired: {ownership.acquired}")

    final_status = probe_robot_ownership()

    print_status(
        "Final ownership state",
        final_status,
    )

    if not final_status.available:
        print()
        print("ERROR: The robot did not become available after the lock was released.")
        return 1

    print()
    print("Robot ownership demo complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
