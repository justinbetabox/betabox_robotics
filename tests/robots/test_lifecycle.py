from betabox_robotics import Robot


def test_robot_supports_context_manager():
    with Robot.default() as robot:
        assert robot is not None


def test_robot_close_is_callable():
    robot = Robot.default()
    robot.close()
