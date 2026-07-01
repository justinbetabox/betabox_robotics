import os
import sys
from contextlib import contextmanager


@contextmanager
def suppress_stderr():
    """
    Suppress C-level stderr noise from ALSA, PyAudio, and ONNX Runtime.
    """
    try:
        sys.stderr.flush()
    except Exception:
        pass

    saved_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)

    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(saved_fd, 2)
        os.close(saved_fd)
        os.close(devnull_fd)
