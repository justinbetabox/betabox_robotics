#!/usr/bin/env python3

from pathlib import Path

from betabox_robotics.system import MediaPaths, System, SystemHealth, SystemStatus


def test_system_status():
    system = System()
    status = system.status()

    print("\nSystem status test")
    print("==================")
    print(f"hostname={status.hostname}")
    print(f"ip_addresses={status.ip_addresses}")
    print(f"version={status.version}")
    print(f"sounds={status.media.sounds}")
    print(f"pictures={status.media.pictures}")
    print(f"videos={status.media.videos}")

    assert isinstance(status.version, str)
    assert status.version != ""
    assert isinstance(status, SystemStatus)
    assert isinstance(status.hostname, str)
    assert status.hostname != ""
    assert isinstance(status.ip_addresses, list)
    assert isinstance(status.media, MediaPaths)
    assert status.media.pictures == Path.home() / "media" / "pictures"
    assert status.media.videos == Path.home() / "media" / "videos"
    assert status.media.sounds == Path.home() / "media" / "sounds"


def test_system_ensure_media_paths():
    system = System()
    paths = system.ensure_media_paths()

    print("\nSystem media paths test")
    print("=======================")
    print(f"pictures_exists={paths.pictures.exists()}")
    print(f"videos_exists={paths.videos.exists()}")
    print(f"sounds_exists={paths.sounds.exists()}")

    assert paths.pictures.exists()
    assert paths.videos.exists()
    assert paths.sounds.exists()
    assert paths.pictures.is_dir()
    assert paths.videos.is_dir()
    assert paths.sounds.is_dir()


def test_system_health():
    system = System()
    system.ensure_media_paths()

    health = system.health()

    print("\nSystem health test")
    print("==================")
    print(f"ok={health.ok}")
    print(f"messages={health.messages}")

    assert isinstance(health, SystemHealth)
    assert health.ok is True
    assert health.messages == []


if __name__ == "__main__":
    test_system_status()
    test_system_ensure_media_paths()
    test_system_health()

    print("\nSystem tests complete.")
