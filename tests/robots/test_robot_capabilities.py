from betabox_robotics import Robot
from betabox_robotics.robots import RobotCapability


def test_robot_has_expected_capabilities():
    robot = Robot.default()

    assert robot.has_capability(RobotCapability.DRIVE)
    assert robot.has_capability(RobotCapability.SENSORS)
    assert robot.has_capability(RobotCapability.VISION)
    assert robot.has_capability(RobotCapability.AUDIO)
    assert robot.has_capability(RobotCapability.SYSTEM)

    robot.close()


def test_robot_has_capability_accepts_string():
    robot = Robot.default()

    assert robot.has_capability("drive")

    robot.close()


def test_robot_capability_names_are_sorted_strings():
    robot = Robot.default()

    assert robot.capability_names() == [
        "audio",
        "drive",
        "sensors",
        "system",
        "vision",
    ]

    robot.close()


if __name__ == "__main__":
    test_robot_has_expected_capabilities()
    test_robot_has_capability_accepts_string()
    test_robot_capability_names_are_sorted_strings()
    print("Robot capability tests passed")
