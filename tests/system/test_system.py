#!/usr/bin/env python3

from pathlib import Path

from betabox_car.system import MediaPaths, System, SystemStatus


def test_system_status():
    system = System()
    status = system.status()

    print("\nSystem status test")
    print("==================")
    print(f"hostname={status.hostname}")
    print(f"ip_addresses={status.ip_addresses}")
    print(f"pictures={status.media.pictures}")
    print(f"videos={status.media.videos}")

    assert isinstance(status, SystemStatus)
    assert isinstance(status.hostname, str)
    assert status.hostname != ""
    assert isinstance(status.ip_addresses, list)
    assert isinstance(status.media, MediaPaths)
    assert status.media.pictures == Path.home() / "media" / "pictures"
    assert status.media.videos == Path.home() / "media" / "videos"


def test_system_ensure_media_paths():
    system = System()
    paths = system.ensure_media_paths()

    print("\nSystem media paths test")
    print("=======================")
    print(f"pictures_exists={paths.pictures.exists()}")
    print(f"videos_exists={paths.videos.exists()}")

    assert paths.pictures.exists()
    assert paths.videos.exists()
    assert paths.pictures.is_dir()
    assert paths.videos.is_dir()


if __name__ == "__main__":
    test_system_status()
    test_system_ensure_media_paths()

    print("\nSystem tests complete.")
