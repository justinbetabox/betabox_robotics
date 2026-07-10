from __future__ import annotations

from betabox_robotics import Robot
from betabox_robotics.audio import AudioStatus
from betabox_robotics.robots import RobotLifecycleError


def main() -> None:
    print()
    print("Betabox Robot Audio API Test")
    print("============================")
    print()

    robot = Robot.default()

    status = robot.audio_status()
    assert isinstance(status, AudioStatus)
    assert status.closed is False

    robot.play_note("C4", 0.1)
    robot.play_melody(
        [
            ("C4", 0.1),
            ("E4", 0.1),
            ("G4", 0.1),
        ],
        gap=0.02,
    )

    robot.stop_all()

    try:
        robot.play_note("C4", 0.1)
    except RobotLifecycleError:
        pass
    else:
        raise AssertionError("stopped robot accepted audio playback")

    robot.start()
    robot.close()

    print("Robot Audio API test passed.")
    print()


if __name__ == "__main__":
    main()
