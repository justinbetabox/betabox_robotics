from unittest.mock import Mock

from betabox_robotics.robots import CarRobot, HealthCheck, RobotHealth
from betabox_robotics.sensors import BatteryState

class FakeCar(CarRobot):
    def __init__(self) -> None:
        super().__init__()
        self.drive = Mock()
        self.audio = Mock()
        self.sensors = Mock()
        self.vision = Mock()
        self.system = Mock()

        self.system = Mock()

        self.system.health.return_value = Mock(
            ok=True,
            messages=[],
        )

        self.sensors.battery.is_critical.return_value = False
        self.sensors.battery.status.return_value = BatteryState.OK

        self.start()


def test_health_returns_robot_health() -> None:
    car = FakeCar()

    health = car.health()

    assert isinstance(health, RobotHealth)
    assert health.ok is True


def test_health_includes_system_check() -> None:
    car = FakeCar()

    health = car.health()

    system_check = health.checks[0]

    assert isinstance(system_check, HealthCheck)
    assert system_check.name == "system"
    assert system_check.ok is True
    car.system.health.assert_called_once_with()


def test_health_includes_battery_check() -> None:
    car = FakeCar()

    health = car.health()

    battery_check = health.checks[1]

    assert battery_check.name == "battery"
    assert battery_check.ok is True
    assert battery_check.message == ""


def test_health_reports_system_failure() -> None:
    car = FakeCar()
    car.system.health.return_value = Mock(
        ok=False,
        messages=["missing pictures directory"],
    )

    health = car.health()

    assert health.ok is False
    assert health.messages == ["missing pictures directory"]


def test_health_reports_critical_battery() -> None:
    car = FakeCar()
    car.sensors.battery.is_critical.return_value = True
    car.sensors.battery.status.return_value = BatteryState.CRITICAL

    health = car.health()

    assert health.ok is False
    assert "battery status: critical" in health.messages


if __name__ == "__main__":
    test_health_returns_robot_health()
    test_health_includes_system_check()
    test_health_includes_battery_check()
    test_health_reports_system_failure()
    test_health_reports_critical_battery()
    print("Robot health tests passed")
