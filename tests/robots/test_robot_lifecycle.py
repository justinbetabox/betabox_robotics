from betabox_robotics import Robot
from betabox_robotics.robots.exceptions import RobotLifecycleError


def main() -> None:
    print()
    print("Betabox Robot Lifecycle Test")
    print("============================")
    print()

    robot = Robot.default()

    assert robot.started is True
    assert robot.closed is False

    robot.start()
    assert robot.started is True

    robot.stop_all()
    assert robot.started is False
    assert robot.closed is False

    robot.start()
    assert robot.started is True

    robot.close()
    assert robot.started is False
    assert robot.closed is True

    robot.close()

    try:
        robot.start()
    except RobotLifecycleError:
        pass
    else:
        raise AssertionError("closed robot was allowed to restart")

    try:
        robot.forward(10)
    except RobotLifecycleError:
        pass
    else:
        raise AssertionError("closed robot accepted movement command")

    print("Robot lifecycle test passed.")
    print()


if __name__ == "__main__":
    main()
