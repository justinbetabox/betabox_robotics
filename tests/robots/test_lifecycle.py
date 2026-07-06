from betabox_robotics import Robot


def test_robot_supports_context_manager():
    with Robot.default() as robot:
        assert robot is not None


def test_robot_close_is_callable():
    robot = Robot.default()
    robot.close()


def test_robot_close_is_idempotent():
    robot = Robot.default()
    robot.close()
    robot.close()
    assert robot.closed is True


def test_context_manager_closes_robot():
    with Robot.default() as robot:
        assert robot.closed is False

    assert robot.closed is True
