from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from betabox_robotics.vision import (
    ClientRecording,
    VisionClient,
    VisionClientError,
)

FFPROBE_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class RecordingTiming:
    requested_duration: float
    elapsed_before_stop: float
    stop_operation_duration: float
    total_elapsed: float


@dataclass(frozen=True, slots=True)
class ProbeResult:
    format_duration: float | None
    stream_duration: float | None
    average_frame_rate: str | None
    real_frame_rate: str | None
    frame_count: int | None


def _parse_optional_float(
    value: object,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        int | float | str,
    ):
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _parse_optional_int(
    value: object,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        int | float | str,
    ):
        return None

    if isinstance(value, float) and not value.is_integer():
        return None

    try:
        return int(value)
    except ValueError:
        return None


def probe_recording(
    path: Path,
) -> ProbeResult | None:
    ffprobe = shutil.which("ffprobe")

    if ffprobe is None:
        return None

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        ("format=duration:stream=avg_frame_rate,r_frame_rate,nb_frames,duration"),
        "-of",
        "json",
        str(path),
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SECONDS,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"Unable to inspect recording with ffprobe: {exc}")
        return None

    try:
        data: dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"Unable to decode ffprobe output: {exc}")
        return None

    format_data = data.get(
        "format",
        {},
    )
    streams = data.get(
        "streams",
        [],
    )

    if not isinstance(
        format_data,
        dict,
    ):
        format_data = {}

    stream_data: dict[str, Any] = {}

    if isinstance(streams, list) and streams and isinstance(streams[0], dict):
        stream_data = streams[0]

    average_frame_rate = stream_data.get("avg_frame_rate")
    real_frame_rate = stream_data.get("r_frame_rate")

    return ProbeResult(
        format_duration=_parse_optional_float(format_data.get("duration")),
        stream_duration=_parse_optional_float(stream_data.get("duration")),
        average_frame_rate=(
            str(average_frame_rate) if average_frame_rate is not None else None
        ),
        real_frame_rate=(str(real_frame_rate) if real_frame_rate is not None else None),
        frame_count=_parse_optional_int(stream_data.get("nb_frames")),
    )


def print_recording(
    recording: ClientRecording,
    timing: RecordingTiming,
    probe: ProbeResult | None,
) -> None:
    expected_encoded_duration = (
        recording.frame_count / recording.fps if recording.fps > 0 else None
    )

    print("Recording complete")
    print("------------------")
    print(f"Path: {recording.path}")
    print(f"Requested duration: {timing.requested_duration:.3f} seconds")
    print(f"Wall time before stop request: {timing.elapsed_before_stop:.3f} seconds")
    print(f"Stop/download/save operation: {timing.stop_operation_duration:.3f} seconds")
    print(f"Total client operation time: {timing.total_elapsed:.3f} seconds")

    print()
    print("Service metadata")
    print("----------------")
    print(f"Reported duration: {recording.duration:.3f} seconds")
    print(f"Frames: {recording.frame_count}")
    print(f"Configured FPS: {recording.fps}")
    print(f"Started: {recording.start_timestamp}")
    print(f"Ended: {recording.end_timestamp}")

    if expected_encoded_duration is not None:
        print(f"Frames / configured FPS: {expected_encoded_duration:.3f} seconds")

    print()
    print("Encoded file")
    print("------------")

    if probe is None:
        print(
            "ffprobe results unavailable. Install ffmpeg to inspect the encoded file."
        )
        return

    print(
        "Container duration: "
        + (
            f"{probe.format_duration:.3f} seconds"
            if probe.format_duration is not None
            else "unavailable"
        )
    )
    print(
        "Video stream duration: "
        + (
            f"{probe.stream_duration:.3f} seconds"
            if probe.stream_duration is not None
            else "unavailable"
        )
    )
    print(f"Average frame rate: {probe.average_frame_rate or 'unavailable'}")
    print(f"Declared frame rate: {probe.real_frame_rate or 'unavailable'}")
    print(
        "Encoded frame count: "
        + (str(probe.frame_count) if probe.frame_count is not None else "unavailable")
    )


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record video through the managed "
            "Betabox Vision service and compare "
            "wall-clock, service, and encoded-file timing."
        )
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help=("Recording duration in seconds. Default: 5."),
    )

    parser.add_argument(
        "--filename",
        help=(
            "Output filename. The .mp4 extension is added or corrected automatically."
        ),
    )

    parser.add_argument(
        "--overlay",
        action="store_true",
        help=("Draw detection metadata onto the recording."),
    )

    parser.add_argument(
        "--source",
        help=("Metadata source to use for the overlay, such as color or face."),
    )

    args = parser.parse_args(argv)

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    if args.source is not None and not args.overlay:
        parser.error("--source requires --overlay")

    client = VisionClient()
    recording_started = False

    recording_started_at: float | None = None
    stop_requested_at: float | None = None
    recording_finished_at: float | None = None

    try:
        output_path = client.start_recording(
            filename=args.filename,
            overlay=args.overlay,
            source=args.source,
        )
        recording_started = True
        recording_started_at = time.monotonic()

        print("Recording started")
        print(f"Planned output: {output_path}")
        print(f"Recording for {args.duration:.2f} seconds...")

        time.sleep(args.duration)

        stop_requested_at = time.monotonic()
        recording = client.stop_recording()
        recording_finished_at = time.monotonic()
        recording_started = False

    except KeyboardInterrupt:
        print()
        print("Recording interrupted.")

        if not recording_started:
            return 1

        try:
            stop_requested_at = time.monotonic()
            recording = client.stop_recording()
            recording_finished_at = time.monotonic()
            recording_started = False
        except VisionClientError as exc:
            print(f"Unable to stop recording cleanly: {exc}")
            return 1

    except (
        TypeError,
        ValueError,
        VisionClientError,
    ) as exc:
        print(f"Unable to complete recording: {exc}")
        return 1

    if (
        recording_started_at is None
        or stop_requested_at is None
        or recording_finished_at is None
    ):
        print("Unable to calculate recording timing.")
        return 1

    timing = RecordingTiming(
        requested_duration=args.duration,
        elapsed_before_stop=(stop_requested_at - recording_started_at),
        stop_operation_duration=(recording_finished_at - stop_requested_at),
        total_elapsed=(recording_finished_at - recording_started_at),
    )

    probe = probe_recording(recording.path)

    print()
    print_recording(
        recording,
        timing,
        probe,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
