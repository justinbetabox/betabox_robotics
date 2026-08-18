from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from betabox_robotics.runtime import RobotRuntimeServer


def _socket_path_from_args(
    args: argparse.Namespace,
) -> Path | None:
    value = cast(
        object,
        getattr(
            args,
            "socket",
            None,
        ),
    )

    if value is None:
        return None

    if not isinstance(
        value,
        Path,
    ):
        raise TypeError("socket must be a Path or None")

    return value


def run_robot_runtime(
    *,
    socket_path: Path | None = None,
) -> int:
    server = (
        RobotRuntimeServer()
        if socket_path is None
        else RobotRuntimeServer(
            socket_path=socket_path,
        )
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()

    return 0


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="betabox robot-runtime")

    _ = parser.add_argument(
        "--socket",
        type=Path,
        default=None,
    )

    args = parser.parse_args(argv)

    return run_robot_runtime(
        socket_path=_socket_path_from_args(args),
    )


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
