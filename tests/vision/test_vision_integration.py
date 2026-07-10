from __future__ import annotations

from pathlib import Path
from time import sleep

from betabox_robotics.vision import VisionClient


def assert_file(path: Path) -> None:
    assert path.exists(), f"missing file: {path}"
    assert path.stat().st_size > 0, f"empty file: {path}"


def main() -> None:
    print()
    print("Betabox Vision Integration Test")
    print("===============================")
    print()

    client = VisionClient()

    print("Checking service statistics...")
    stats = client.statistics()

    assert stats["running"] is True
    assert stats["camera"]["running"] is True
    assert stats["camera"]["has_frame"] is True
    assert stats["streaming"]["running"] is True

    print("Capturing plain snapshot...")
    snapshot = client.snapshot(
        filename="integration_plain.jpg",
    )
    assert_file(snapshot.path)

    print("Checking detector status...")
    detection = client.detection_status()

    assert "color" in detection["detectors"]

    print("Enabling color detector...")
    client.enable_detection("color")
    sleep(2)

    detection = client.detection_status()
    assert detection["enabled"]["color"] is True

    print("Checking color metadata...")

    metadata = {}

    for _ in range(20):
        metadata = client.metadata("color")

        if metadata.get("source") == "color":
            break

        sleep(0.1)

    assert metadata.get("source") == "color"

    print("Capturing overlay snapshot...")
    overlay_snapshot = client.snapshot(
        filename="integration_overlay.jpg",
        overlay=True,
        source="color",
    )
    assert_file(overlay_snapshot.path)

    print("Enabling WebRTC overlay...")
    stream_overlay = client.enable_stream_overlay("color")
    assert stream_overlay["enabled"] is True
    assert stream_overlay["source"] == "color"

    print("Starting overlay recording...")
    recording_path = client.start_recording(
        filename="integration_overlay.mp4",
        overlay=True,
        source="color",
    )

    sleep(3)

    recording = client.stop_recording()

    assert recording.path == recording_path
    assert recording.frame_count > 0
    assert recording.duration > 0
    assert_file(recording.path)

    print("Disabling WebRTC overlay...")
    stream_overlay = client.disable_stream_overlay()
    assert stream_overlay["enabled"] is False

    print("Disabling color detector...")
    client.disable_detection("color")

    detection = client.detection_status()
    assert detection["enabled"]["color"] is False

    print("Checking final service statistics...")
    final_stats = client.statistics()

    assert final_stats["recording"]["active"] is False
    assert final_stats["streaming"]["overlay"]["enabled"] is False
    assert final_stats["detection"]["detectors"]["color"] is False

    print()
    print("Vision integration test passed.")
    print()


if __name__ == "__main__":
    main()
