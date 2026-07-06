from unittest.mock import Mock

from betabox_robotics.robots import CarRobot


class FakeCar(CarRobot):
    def __init__(self):
        self.drive = Mock()
        self.audio = Mock()
        self.sensors = Mock()
        self.sensors.ultrasonic.distance.return_value = 42.0


def test_forward_delegates_to_drive():
    car = FakeCar()

    car.forward(50)

    car.drive.forward.assert_called_once_with(50)


def test_backward_delegates_to_drive():
    car = FakeCar()

    car.backward(30)

    car.drive.backward.assert_called_once_with(30)


def test_stop_delegates_to_drive():
    car = FakeCar()

    car.stop()

    car.drive.stop.assert_called_once_with()


def test_left_delegates_to_drive():
    car = FakeCar()

    car.left(20)

    car.drive.left.assert_called_once_with(20)


def test_left_uses_default_angle():
    car = FakeCar()

    car.left()

    car.drive.left.assert_called_once_with(30)


def test_right_delegates_to_drive():
    car = FakeCar()

    car.right(20)

    car.drive.right.assert_called_once_with(20)


def test_right_uses_default_angle():
    car = FakeCar()

    car.right()

    car.drive.right.assert_called_once_with(30)


def test_center_delegates_to_drive():
    car = FakeCar()

    car.center()

    car.drive.center.assert_called_once_with()


def test_say_delegates_to_audio():
    car = FakeCar()

    car.say("Hello")

    car.audio.say.assert_called_once_with("Hello")


def test_distance_delegates_to_ultrasonic():
    car = FakeCar()

    distance = car.distance()

    assert distance == 42.0
    car.sensors.ultrasonic.distance.assert_called_once_with()


def test_capture_delegates_to_vision_snapshot():
    car = FakeCar()
    car.vision = Mock()
    car.vision.snapshot.capture.return_value = "snapshot.jpg"

    result = car.capture("snapshot.jpg")

    assert result == "snapshot.jpg"
    car.vision.snapshot.capture.assert_called_once_with(filename="snapshot.jpg")


def test_capture_without_path_delegates_to_vision_snapshot():
    car = FakeCar()
    car.vision = Mock()
    car.vision.snapshot.capture.return_value = "snapshot.jpg"

    result = car.capture()

    assert result == "snapshot.jpg"
    car.vision.snapshot.capture.assert_called_once_with(filename=None)


def test_start_recording_delegates_to_vision_recording():
    car = FakeCar()
    car.vision = Mock()
    car.vision.recording.start.return_value = "demo.mp4"

    result = car.start_recording("demo.mp4")

    assert result == "demo.mp4"
    car.vision.recording.start.assert_called_once_with(filename="demo.mp4")


def test_stop_recording_delegates_to_vision_recording():
    car = FakeCar()
    car.vision = Mock()
    car.vision.recording.stop.return_value = "recording"

    result = car.stop_recording()

    assert result == "recording"
    car.vision.recording.stop.assert_called_once_with()


def test_is_recording_delegates_to_vision_recording():
    car = FakeCar()
    car.vision = Mock()
    car.vision.recording.is_recording.return_value = True

    result = car.is_recording()

    assert result is True
    car.vision.recording.is_recording.assert_called_once_with()


def test_play_delegates_to_audio():
    car = FakeCar()

    car.play("sound.wav")

    car.audio.play.assert_called_once_with("sound.wav")


def test_play_note_delegates_to_audio():
    car = FakeCar()

    car.play_note("C4", 0.5)

    car.audio.play_note.assert_called_once_with("C4", 0.5)


def test_play_melody_delegates_to_audio():
    car = FakeCar()
    melody = [("C4", 0.25), ("E4", 0.25)]

    car.play_melody(melody, gap=0.1)

    car.audio.play_melody.assert_called_once_with(melody, gap=0.1)


def test_stop_audio_delegates_to_audio():
    car = FakeCar()

    car.stop_audio()

    car.audio.stop.assert_called_once_with()


def test_is_audio_playing_delegates_to_audio():
    car = FakeCar()
    car.audio.is_playing.return_value = False

    result = car.is_audio_playing()

    assert result is False
    car.audio.is_playing.assert_called_once_with()
