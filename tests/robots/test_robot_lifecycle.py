from unittest.mock import Mock

from betabox_robotics.robots import CarRobot


class FakeCar(CarRobot):
    def __init__(self):
        super().__init__()

        self.drive = Mock()
        self.audio = Mock()
        self.sensors = Mock()
        self.vision = Mock()
        self.system = Mock()

        self.vision.recording.is_recording.return_value = False
        self.vision.is_running.return_value = False


def test_stop_only_stops_drive():
    car = FakeCar()

    car.stop()

    car.drive.stop.assert_called_once_with()
    car.audio.stop.assert_not_called()
    car.vision.stop.assert_not_called()
    car.system.stop_all.assert_not_called()


def test_stop_all_stops_drive_audio_vision_and_system():
    car = FakeCar()
    car.vision.recording.is_recording.return_value = False
    car.vision.is_running.return_value = True

    car.stop_all()

    car.drive.stop.assert_called_once_with()
    car.audio.stop.assert_called_once_with()
    car.vision.stop.assert_called_once_with()
    car.system.stop_all.assert_called_once_with()


def test_stop_all_stops_recording_when_recording():
    car = FakeCar()
    car.vision.recording.is_recording.return_value = True

    car.stop_all()

    car.vision.recording.stop.assert_called_once_with()


def test_stop_all_does_not_stop_recording_when_not_recording():
    car = FakeCar()
    car.vision.recording.is_recording.return_value = False

    car.stop_all()

    car.vision.recording.stop.assert_not_called()


def test_start_sets_started_state():
    car = FakeCar()

    car.start()

    assert car.started is True
    assert car.closed is False


def test_stop_all_clears_started_state():
    car = FakeCar()

    car.start()
    car.stop_all()

    assert car.started is False
    assert car.closed is False


def test_close_is_idempotent():
    car = FakeCar()

    car.close()
    car.close()

    assert car.closed is True


if __name__ == "__main__":
    test_stop_only_stops_drive()
    test_stop_all_stops_drive_audio_vision_and_system()
    test_stop_all_stops_recording_when_recording()
    test_stop_all_does_not_stop_recording_when_not_recording()
    test_start_sets_started_state()
    test_stop_all_clears_started_state()
    test_close_is_idempotent()
    print("Robot lifecycle tests passed")
