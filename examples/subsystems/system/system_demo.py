#!/usr/bin/env python3
"""
Developer demo for the Betabox System subsystem.
"""

from betabox_robotics.robots import BETABOX_CAR
from betabox_robotics.system import System


def main() -> None:
    print()
    print("Betabox System Demo")
    print("===================")
    print()

    system = System.default(BETABOX_CAR)

    status = system.status()

    print(f"Hostname: {status.hostname}")

    print()
    print("IP Addresses:")
    if status.ip_addresses:
        for address in status.ip_addresses:
            print(f"  {address}")
    else:
        print("  None")

    print()
    print("Media Paths:")
    print(f"  Pictures: {status.media.pictures}")
    print(f"  Videos:   {status.media.videos}")
    print(f"  Sounds:   {status.media.sounds}")

    print()
    print("Ensuring media directories exist...")
    system.ensure_media_paths()

    print()
    print("System demo complete.")


if __name__ == "__main__":
    main()
