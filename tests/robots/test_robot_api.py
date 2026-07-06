from betabox_robotics import BetaboxCar, Car, Robot
from betabox_robotics.robots import CarRobot, RobotBase


def test_robot_default_returns_betabox_car():
    robot = Robot.default()

    assert isinstance(robot, BetaboxCar)
    assert isinstance(robot, CarRobot)
    assert isinstance(robot, RobotBase)

    robot.close()


def test_car_alias_is_betabox_car():
    car = Car()

    assert isinstance(car, BetaboxCar)

    car.close()


def test_robot_exposes_expected_subsystems():
    robot = Robot.default()

    assert hasattr(robot, "drive")
    assert hasattr(robot, "sensors")
    assert hasattr(robot, "vision")
    assert hasattr(robot, "audio")
    assert hasattr(robot, "system")

    robot.close()
