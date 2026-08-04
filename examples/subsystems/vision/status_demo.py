from __future__ import annotations

from betabox_robotics.vision import (
    ClientStreamOverlayStatus,
    ClientVisionStatistics,
    VisionClient,
    VisionClientError,
)


def print_overlay(
    name: str,
    overlay: ClientStreamOverlayStatus,
) -> None:
    source = overlay.source if overlay.source is not None else "latest"

    print(f"{name}: enabled={overlay.enabled}, source={source}")


def print_statistics(
    statistics: ClientVisionStatistics,
) -> None:
    print("Betabox Vision Status")
    print("=====================")

    print()
    print("Service")
    print("-------")
    print(f"Running: {statistics.running}")
    print(f"Address: http://{statistics.server.host}:{statistics.server.port}")
    print(f"Configured FPS: {statistics.server.fps}")

    print()
    print("Camera")
    print("------")
    print(f"Running: {statistics.camera.running}")
    print(f"FPS: {statistics.camera.fps}")
    print(f"Consumers: {statistics.camera.consumer_count}")
    print(f"Frame available: {statistics.camera.has_frame}")
    print(f"Last error: {statistics.camera.last_error or 'none'}")

    print()
    print("Streaming")
    print("---------")
    print(f"Running: {statistics.streaming.running}")
    print(f"Clients: {statistics.streaming.clients}")
    print(f"Frames received: {statistics.streaming.frames_received}")
    print(f"Frame available: {statistics.streaming.has_frame}")
    print_overlay(
        "Overlay",
        statistics.streaming.overlay,
    )

    print()
    print("Recording")
    print("---------")
    print(f"Active: {statistics.recording.active}")
    print_overlay(
        "Overlay",
        statistics.recording.overlay,
    )

    print()
    print("Detection")
    print("---------")

    for name, enabled in sorted(statistics.detection.detectors.items()):
        state = "enabled" if enabled else "disabled"

        print(f"{name}: {state}")

    sources = ", ".join(statistics.detection.metadata_sources) or "none"

    print(f"Metadata sources: {sources}")


def main() -> int:
    client = VisionClient()

    try:
        statistics = client.statistics()
    except VisionClientError as exc:
        print(f"Unable to read Vision status: {exc}")
        return 1

    print_statistics(statistics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
