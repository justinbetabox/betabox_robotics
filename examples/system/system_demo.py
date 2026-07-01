#!/usr/bin/env python3
"""
Developer demo for the Betabox System subsystem.
"""

from betabox_car.system import System


def main() -> None:
    system = System()

    print()
    print("Betabox System Demo")
    print("===================")
    print()

    status = system.status()

    print(f"Hostname: {status.hostname}")

    print("\nIP Addresses:")
    if status.ip_addresses:
        for address in status.ip_addresses:
            print(f"  {address}")
    else:
        print("  None")

    print("\nMedia Paths:")
    print(f"  Pictures: {status.media.pictures}")
    print(f"  Videos:   {status.media.videos}")
    print(f"  Sounds:   {status.media.sounds}")

    print()
    print("Ensuring media directories exist...")
    system.ensure_media_paths()

    print("Done.")


if __name__ == "__main__":
    main()
