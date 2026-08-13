import os
import sys
from collections.abc import Generator
from contextlib import contextmanager


@contextmanager
def suppress_stderr() -> Generator[None, None, None]:
    """
    Suppress C-level stderr noise from ALSA, PyAudio, and ONNX Runtime.
    """
    try:
        _ = sys.stderr.flush()
    except (OSError, RuntimeError):
        pass

    saved_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)

    try:
        _ = os.dup2(devnull_fd, 2)
        yield
    finally:
        _ = os.dup2(saved_fd, 2)
        os.close(saved_fd)
        os.close(devnull_fd)
