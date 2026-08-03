from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from betabox_robotics.robots import CarRobot
from betabox_robotics.vision import (
    ClientDetection,
    ClientMetadata,
)


class FakeCar(CarRobot):
    def __init__(self) -> None:
        super().__init__()

        self.drive = MagicMock()
        self.audio = MagicMock()
        self.sensors = MagicMock()
        self.camera_mount = MagicMock()
        self.vision = MagicMock()
        self.system = MagicMock()

        self.sensors.ultrasonic.distance.return_value = 42.0

        # Mark the fake robot as ready for public convenience methods.
        self._opened = True
        self._started = True


class CarRobotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = FakeCar()

    def test_forward_delegates_to_drive(self) -> None:
        self.car.forward(50)

        self.car.drive.forward.assert_called_once_with(50)

    def test_backward_delegates_to_drive(self) -> None:
        self.car.backward(30)

        self.car.drive.backward.assert_called_once_with(30)

    def test_stop_delegates_to_drive(self) -> None:
        self.car.stop()

        self.car.drive.stop.assert_called_once_with()

    def test_left_delegates_to_drive(self) -> None:
        self.car.left(20)

        self.car.drive.left.assert_called_once_with(20)

    def test_left_uses_default_angle(self) -> None:
        self.car.left()

        self.car.drive.left.assert_called_once_with(30)

    def test_right_delegates_to_drive(self) -> None:
        self.car.right(20)

        self.car.drive.right.assert_called_once_with(20)

    def test_right_uses_default_angle(self) -> None:
        self.car.right()

        self.car.drive.right.assert_called_once_with(30)

    def test_center_delegates_to_drive(self) -> None:
        self.car.center()

        self.car.drive.center.assert_called_once_with()

    def test_look_delegates_to_camera_mount(self) -> None:
        self.car.look(
            pan=20,
            tilt=-10,
            smooth=False,
        )

        self.car.camera_mount.look.assert_called_once_with(
            pan=20,
            tilt=-10,
            smooth=False,
        )

    def test_camera_pan_delegates(self) -> None:
        self.car.camera_pan(
            20,
            smooth=False,
        )

        self.car.camera_mount.pan.assert_called_once_with(
            20,
            smooth=False,
        )

    def test_camera_tilt_delegates(self) -> None:
        self.car.camera_tilt(
            -10,
            smooth=False,
        )

        self.car.camera_mount.tilt.assert_called_once_with(
            -10,
            smooth=False,
        )

    def test_look_center_delegates(self) -> None:
        self.car.look_center(
            smooth=False,
        )

        self.car.camera_mount.center.assert_called_once_with(
            smooth=False,
        )

    def test_say_delegates_to_audio(self) -> None:
        self.car.say("Hello")

        self.car.audio.say.assert_called_once_with("Hello")

    def test_play_delegates_to_audio(self) -> None:
        self.car.play("sound.wav")

        self.car.audio.play.assert_called_once_with("sound.wav")

    def test_play_note_delegates_to_audio(self) -> None:
        self.car.play_note("C4", 0.5)

        self.car.audio.play_note.assert_called_once_with(
            "C4",
            0.5,
        )

    def test_play_melody_delegates_to_audio(self) -> None:
        melody = [
            ("C4", 0.25),
            ("E4", 0.25),
        ]

        self.car.play_melody(
            melody,
            gap=0.1,
        )

        self.car.audio.play_melody.assert_called_once_with(
            melody,
            gap=0.1,
        )

    def test_stop_audio_delegates_to_audio(self) -> None:
        self.car.stop_audio()

        self.car.audio.stop.assert_called_once_with()

    def test_is_audio_playing_delegates_to_audio(self) -> None:
        self.car.audio.is_playing.return_value = False

        result = self.car.is_audio_playing()

        self.assertFalse(result)
        self.car.audio.is_playing.assert_called_once_with()

    def test_distance_delegates_to_ultrasonic(self) -> None:
        result = self.car.distance()

        self.assertEqual(result, 42.0)
        self.car.sensors.ultrasonic.distance.assert_called_once_with(10)

    def test_distance_passes_samples(self) -> None:
        self.car.distance(samples=5)

        self.car.sensors.ultrasonic.distance.assert_called_once_with(5)

    def test_capture_delegates_to_vision_snapshot(self) -> None:
        expected = MagicMock()
        self.car.vision.snapshot.return_value = expected

        result = self.car.capture(
            filename="snapshot.jpg",
            overlay=True,
            source="color",
        )

        self.assertIs(result, expected)
        self.car.vision.snapshot.assert_called_once_with(
            filename="snapshot.jpg",
            overlay=True,
            source="color",
        )

    def test_capture_without_filename(self) -> None:
        expected = MagicMock()
        self.car.vision.snapshot.return_value = expected

        result = self.car.capture()

        self.assertIs(result, expected)
        self.car.vision.snapshot.assert_called_once_with(
            filename=None,
            overlay=False,
            source=None,
        )

    def test_start_recording_delegates_to_vision_client(
        self,
    ) -> None:
        expected = Path("/tmp/demo.mp4")
        self.car.vision.start_recording.return_value = expected

        result = self.car.start_recording(
            filename="demo.mp4",
            overlay=True,
            source="color",
        )

        self.assertEqual(result, expected)
        self.assertTrue(self.car._recording_started_by_robot)

        self.car.vision.start_recording.assert_called_once_with(
            filename="demo.mp4",
            overlay=True,
            source="color",
        )

    def test_stop_recording_delegates_to_vision_client(
        self,
    ) -> None:
        expected = MagicMock()
        self.car._recording_started_by_robot = True
        self.car.vision.stop_recording.return_value = expected

        result = self.car.stop_recording()

        self.assertIs(result, expected)
        self.assertFalse(self.car._recording_started_by_robot)
        self.car.vision.stop_recording.assert_called_once_with()

    def test_is_recording_uses_vision_statistics(self) -> None:
        statistics = MagicMock()
        statistics.recording.active = True
        self.car.vision.statistics.return_value = statistics

        result = self.car.is_recording()

        self.assertTrue(result)
        self.car.vision.statistics.assert_called_once_with()

    def test_enable_detection_delegates(self) -> None:
        expected = MagicMock()
        self.car.vision.enable_detection.return_value = expected

        result = self.car.enable_detection("face")

        self.assertIs(result, expected)
        self.car.vision.enable_detection.assert_called_once_with("face")

    def test_disable_detection_delegates(self) -> None:
        expected = MagicMock()
        self.car.vision.disable_detection.return_value = expected

        result = self.car.disable_detection("face")

        self.assertIs(result, expected)
        self.car.vision.disable_detection.assert_called_once_with("face")

    def test_enable_color_detection_delegates(self) -> None:
        expected = MagicMock()
        self.car.vision.enable_color_detection.return_value = expected

        result = self.car.enable_color_detection(
            [
                "red",
                "green",
                "blue",
                "yellow",
            ],
            min_area=250,
        )

        self.assertIs(result, expected)
        self.car.vision.enable_color_detection.assert_called_once_with(
            [
                "red",
                "green",
                "blue",
                "yellow",
            ],
            min_area=250,
        )

    def test_disable_color_detection_delegates(self) -> None:
        expected = MagicMock()
        self.car.vision.disable_detection.return_value = expected

        result = self.car.disable_color_detection()

        self.assertIs(result, expected)
        self.car.vision.disable_detection.assert_called_once_with("color")

    def test_metadata_delegates(self) -> None:
        expected = MagicMock()
        self.car.vision.metadata.return_value = expected

        result = self.car.metadata("color")

        self.assertIs(result, expected)
        self.car.vision.metadata.assert_called_once_with("color")

    def test_enable_stream_overlay_delegates(self) -> None:
        expected = MagicMock()
        self.car.vision.enable_stream_overlay.return_value = expected

        result = self.car.enable_stream_overlay("color")

        self.assertIs(result, expected)
        self.car.vision.enable_stream_overlay.assert_called_once_with("color")

    def test_disable_stream_overlay_delegates(self) -> None:
        expected = MagicMock()
        self.car.vision.disable_stream_overlay.return_value = expected

        result = self.car.disable_stream_overlay()

        self.assertIs(result, expected)
        self.car.vision.disable_stream_overlay.assert_called_once_with()

    def test_sees_color_returns_true_for_matching_detection(
        self,
    ) -> None:
        self.car.vision.metadata.return_value = ClientMetadata(
            source="color",
            timestamp=1.0,
            detections=[
                ClientDetection(
                    label="red",
                    confidence=None,
                    box=(10, 20, 30, 40),
                    center=(25, 40),
                    data={
                        "area": 1200.0,
                    },
                ),
            ],
            data={},
        )

        self.assertTrue(self.car.sees_color("RED"))

    def test_color_count_counts_matching_regions(
        self,
    ) -> None:
        self.car.vision.metadata.return_value = ClientMetadata(
            source="color",
            timestamp=1.0,
            detections=[
                ClientDetection(
                    label="red",
                    confidence=None,
                    box=None,
                    center=None,
                    data={},
                ),
                ClientDetection(
                    label="blue",
                    confidence=None,
                    box=None,
                    center=None,
                    data={},
                ),
                ClientDetection(
                    label="red",
                    confidence=None,
                    box=None,
                    center=None,
                    data={},
                ),
            ],
            data={},
        )

        self.assertEqual(
            self.car.color_count("red"),
            2,
        )

    def test_visible_colors_are_unique_and_sorted(
        self,
    ) -> None:
        self.car.vision.metadata.return_value = ClientMetadata(
            source="color",
            timestamp=1.0,
            detections=[
                ClientDetection(
                    label="red",
                    confidence=None,
                    box=None,
                    center=None,
                    data={},
                ),
                ClientDetection(
                    label="blue",
                    confidence=None,
                    box=None,
                    center=None,
                    data={},
                ),
                ClientDetection(
                    label="red",
                    confidence=None,
                    box=None,
                    center=None,
                    data={},
                ),
            ],
            data={},
        )

        self.assertEqual(
            self.car.visible_colors(),
            ["blue", "red"],
        )

    def test_largest_color_uses_detection_area(
        self,
    ) -> None:
        small = ClientDetection(
            label="red",
            confidence=None,
            box=None,
            center=(10, 10),
            data={
                "area": 100.0,
            },
        )
        large = ClientDetection(
            label="red",
            confidence=None,
            box=None,
            center=(50, 50),
            data={
                "area": 900.0,
            },
        )

        self.car.vision.metadata.return_value = ClientMetadata(
            source="color",
            timestamp=1.0,
            detections=[
                small,
                large,
            ],
            data={},
        )

        self.assertIs(
            self.car.largest_color("red"),
            large,
        )
        self.assertEqual(
            self.car.color_center("red"),
            (50, 50),
        )
        self.assertEqual(
            self.car.color_area("red"),
            900.0,
        )

    def test_face_helpers(self) -> None:
        small = ClientDetection(
            label="face",
            confidence=None,
            box=(0, 0, 20, 20),
            center=(10, 10),
            data={},
        )
        large = ClientDetection(
            label="face",
            confidence=None,
            box=(0, 0, 50, 40),
            center=(25, 20),
            data={},
        )

        self.car.vision.metadata.return_value = ClientMetadata(
            source="face",
            timestamp=1.0,
            detections=[
                small,
                large,
            ],
            data={},
        )

        self.assertTrue(self.car.sees_face())
        self.assertEqual(
            self.car.face_count(),
            2,
        )
        self.assertIs(
            self.car.largest_face(),
            large,
        )
        self.assertEqual(
            self.car.face_center(),
            (25, 20),
        )
        self.assertEqual(
            self.car.face_centers(),
            [
                (10, 10),
                (25, 20),
            ],
        )

    def test_detection_helpers_return_empty_values_without_metadata(
        self,
    ) -> None:
        self.car.vision.metadata.return_value = None

        self.assertFalse(self.car.sees_color("red"))
        self.assertEqual(
            self.car.color_count("red"),
            0,
        )
        self.assertEqual(
            self.car.visible_colors(),
            [],
        )
        self.assertIsNone(self.car.color_center("red"))
        self.assertIsNone(self.car.color_area("red"))

        self.assertFalse(self.car.sees_face())
        self.assertEqual(
            self.car.face_count(),
            0,
        )
        self.assertIsNone(self.car.face_center())
        self.assertEqual(
            self.car.face_centers(),
            [],
        )


if __name__ == "__main__":
    unittest.main()
