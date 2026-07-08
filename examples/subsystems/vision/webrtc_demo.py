#!/usr/bin/env python3
"""
Developer demo for the Betabox Vision WebRTC service.
"""

from betabox_robotics.vision import VisionService, VisionServiceConfig


def main() -> None:
    print()
    print("Betabox Vision WebRTC Demo")
    print("==========================")
    print()
    print("Open this URL in a browser:")
    print("    http://<robot-ip>:8080")
    print()
    print("Press Ctrl+C to stop.")
    print()

    service = VisionService(VisionServiceConfig(host="0.0.0.0", port=8080, fps=20))

    try:
        service.run()
    except KeyboardInterrupt:
        print()
        print("Stopping...")
    finally:
        service.stop()

    print()
    print("Vision WebRTC demo complete.")


if __name__ == "__main__":
    main()
