from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final

from betabox_robotics.audio.exceptions import SpeechError

SPEECH_TIMEOUT_SECONDS: Final[float] = 30.0


def validate_speech_request(
    text: object,
    output_path: str | Path,
) -> tuple[str, Path]:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not text.strip():
        raise ValueError("text cannot be empty")

    if isinstance(output_path, bool) or not isinstance(
        output_path,
        str | Path,
    ):
        raise TypeError("output_path must be a string or Path")

    path = Path(output_path).expanduser()

    if path.exists() and path.is_dir():
        raise ValueError("output_path must not be a directory")

    if path.suffix.lower() != ".wav":
        raise ValueError("output_path must use the .wav extension")

    return text, path


def run_speech_command(
    command: list[str],
    *,
    backend_name: str,
    input_text: str | None = None,
    timeout: float = SPEECH_TIMEOUT_SECONDS,
) -> None:
    try:
        result = subprocess.run(
            command,
            input=input_text,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

    except subprocess.TimeoutExpired as exc:
        raise SpeechError(
            f"{backend_name} speech timed out after {timeout:g} seconds"
        ) from exc

    except OSError as exc:
        raise SpeechError(f"failed to start {backend_name}: {exc}") from exc

    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() if exc.stderr else ""

        message = (
            f"{backend_name} speech failed: {details}"
            if details
            else f"{backend_name} speech failed"
        )

        raise SpeechError(message) from exc

    if result.returncode != 0:
        raise SpeechError(f"{backend_name} speech failed")


def verify_speech_output(
    output_path: Path,
    *,
    backend_name: str,
) -> None:
    try:
        valid_output = output_path.is_file() and output_path.stat().st_size > 0
    except OSError as exc:
        raise SpeechError(f"failed to inspect {backend_name} output: {exc}") from exc

    if not valid_output:
        raise SpeechError(f"{backend_name} did not create a valid WAV file")
