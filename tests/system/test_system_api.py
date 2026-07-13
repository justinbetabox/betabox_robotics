from __future__ import annotations

from betabox_robotics.system import (
    MediaPaths,
    System,
    SystemError,
    SystemHealth,
    SystemStatus,
)
from robots.betabox_car import BETABOX_CAR


def main() -> None:
    print()
    print("Betabox System API Test")
    print("=======================")
    print()

    system = System.default(BETABOX_CAR.system)

    assert system.closed is False
    assert isinstance(system.hostname(), str)
    assert isinstance(system.ip_addresses(), list)

    media = system.media_paths()
    assert isinstance(media, MediaPaths)

    ensured = system.ensure_media_paths()
    assert isinstance(ensured, MediaPaths)
    assert ensured.exists()

    status = system.status()
    assert isinstance(status, SystemStatus)
    print(status.to_dict())

    health = system.health()
    assert isinstance(health, SystemHealth)
    assert health.ok is True

    system.stop_all()
    system.close()
    system.close()

    assert system.closed is True

    try:
        system.status()
    except SystemError:
        pass
    else:
        raise AssertionError("closed System accepted an operation")

    print("System API test passed.")
    print()


if __name__ == "__main__":
    main()
