from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from betabox_robotics.robots.capabilities import (
    RobotCapability,
)
from betabox_robotics.robots.car import (
    CarRobot,
    _detection_area,
    _validate_name,
)
from betabox_robotics.robots.exceptions import (
    RobotLifecycleError,
)
from betabox_robotics.robots.health import (
    RobotHealth,
)
from betabox_robotics.system import (
    MediaPaths,
    SystemHealth,
)


class TestCar(CarRobot):
    """
    Hardware-free CarRobot used to test the convenience façade.
    """

    __test__ = False

    def __init__(self) -> None:
        super().__init__()

        self.drive = MagicMock()
        self.camera_mount = MagicMock()
        self.audio = MagicMock()
        self.vision = MagicMock()
        self.system = MagicMock()

        self.sensors = MagicMock()
        self.sensors.ultrasonic = MagicMock()
        self.sensors.battery = MagicMock()
        self.sensors.grayscale = MagicMock()


def make_detection(
    *,
    label: str,
    area: object = 0.0,
    center: tuple[int, int] | None = None,
    box: tuple[int, int, int, int] | None = None,
) -> object:
    return SimpleNamespace(
        label=label,
        data={
            "area": area,
        },
        center=center,
        box=box,
    )


class ValidateNameTests(unittest.TestCase):
    def test_accepts_and_normalizes_string(self) -> None:
        self.assertEqual(
            _validate_name(
                " Color ",
                name="source",
            ),
            "Color",
        )

    def test_rejects_empty_string(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "source cannot be empty",
                ),
            ):
                _validate_name(
                    value,
                    name="source",
                )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            1,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "source must be a string",
                ),
            ):
                _validate_name(
                    value,
                    name="source",
                )


class DetectionAreaTests(unittest.TestCase):
    def test_accepts_numeric_area(self) -> None:
        detection = make_detection(
            label="red",
            area="125.5",
        )

        self.assertEqual(
            _detection_area(
                detection  # type: ignore[arg-type]
            ),
            125.5,
        )

    def test_negative_area_becomes_zero(self) -> None:
        detection = make_detection(
            label="red",
            area=-10,
        )

        self.assertEqual(
            _detection_area(
                detection  # type: ignore[arg-type]
            ),
            0.0,
        )

    def test_boolean_area_becomes_zero(self) -> None:
        detection = make_detection(
            label="red",
            area=True,
        )

        self.assertEqual(
            _detection_area(
                detection  # type: ignore[arg-type]
            ),
            0.0,
        )

    def test_invalid_area_becomes_zero(self) -> None:
        for value in (
            None,
            object(),
            "invalid",
        ):
            with self.subTest(value=value):
                detection = make_detection(
                    label="red",
                    area=value,
                )

                self.assertEqual(
                    _detection_area(
                        detection  # type: ignore[arg-type]
                    ),
                    0.0,
                )

    def test_missing_area_becomes_zero(self) -> None:
        detection = SimpleNamespace(
            data={},
        )

        self.assertEqual(
            _detection_area(
                detection  # type: ignore[arg-type]
            ),
            0.0,
        )


class CarRobotConstructionTests(unittest.TestCase):
    def test_inherits_expected_capabilities(self) -> None:
        car = TestCar()

        self.assertEqual(
            car.capabilities,
            frozenset(
                {
                    RobotCapability.DRIVE,
                    RobotCapability.SENSORS,
                    RobotCapability.VISION,
                    RobotCapability.AUDIO,
                    RobotCapability.SYSTEM,
                }
            ),
        )

    def test_initial_recording_ownership_is_false(
        self,
    ) -> None:
        car = TestCar()

        self.assertFalse(car._recording_started_by_robot)

    def test_operations_require_started_robot(
        self,
    ) -> None:
        car = TestCar()

        with self.assertRaisesRegex(
            RobotLifecycleError,
            "robot is not started",
        ):
            car.forward(50)

        car.drive.forward.assert_not_called()


class CarRobotDriveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def test_drive_methods_delegate(self) -> None:
        self.car.forward(50)
        self.car.backward(40)
        self.car.stop()
        self.car.left(15)
        self.car.right(20)
        self.car.center()

        self.car.drive.forward.assert_called_once_with(50)
        self.car.drive.backward.assert_called_once_with(40)
        self.car.drive.stop.assert_called_once_with()
        self.car.drive.left.assert_called_once_with(15)
        self.car.drive.right.assert_called_once_with(20)
        self.car.drive.center.assert_called_once_with()

    def test_default_turn_angles(self) -> None:
        self.car.left()
        self.car.right()

        self.car.drive.left.assert_called_once_with(30)
        self.car.drive.right.assert_called_once_with(30)

    def test_drive_status(self) -> None:
        expected = object()
        self.car.drive.status.return_value = expected

        result = self.car.drive_status()

        self.assertIs(
            result,
            expected,
        )
        self.car.drive.status.assert_called_once_with()


class CarRobotCameraMountTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def test_camera_methods_delegate(self) -> None:
        self.car.look(
            pan=10,
            tilt=-5,
            smooth=False,
        )
        self.car.camera_pan(
            20,
            smooth=False,
        )
        self.car.camera_tilt(
            -10,
            smooth=True,
        )
        self.car.look_center(smooth=False)

        self.car.camera_mount.look.assert_called_once_with(
            pan=10,
            tilt=-5,
            smooth=False,
        )
        self.car.camera_mount.pan.assert_called_once_with(
            20,
            smooth=False,
        )
        self.car.camera_mount.tilt.assert_called_once_with(
            -10,
            smooth=True,
        )
        self.car.camera_mount.center.assert_called_once_with(smooth=False)

    def test_camera_mount_status(self) -> None:
        expected = object()
        self.car.camera_mount.status.return_value = expected

        result = self.car.camera_mount_status()

        self.assertIs(
            result,
            expected,
        )


class CarRobotAudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def test_audio_methods_delegate(self) -> None:
        notes = (
            ("C4", 0.5),
            ("E4", 0.5),
        )

        self.car.say("Hello")
        self.car.play(Path("/tmp/sound.wav"))
        self.car.play_note(
            "C4",  # type: ignore[arg-type]
            0.5,
        )
        self.car.play_melody(
            notes,  # type: ignore[arg-type]
            gap=0.1,
        )
        self.car.stop_audio()

        self.car.audio.say.assert_called_once_with("Hello")
        self.car.audio.play.assert_called_once_with(Path("/tmp/sound.wav"))
        self.car.audio.play_note.assert_called_once_with(
            "C4",
            0.5,
        )
        self.car.audio.play_melody.assert_called_once_with(
            notes,
            gap=0.1,
        )
        self.car.audio.stop.assert_called_once_with()

    def test_is_audio_playing(self) -> None:
        self.car.audio.is_playing.return_value = True

        self.assertTrue(self.car.is_audio_playing())

    def test_audio_status(self) -> None:
        expected = object()
        self.car.audio.status.return_value = expected

        self.assertIs(
            self.car.audio_status(),
            expected,
        )


class CarRobotSensorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def test_ultrasonic_methods_delegate(self) -> None:
        reading = object()

        self.car.sensors.ultrasonic.distance.return_value = 42.5
        self.car.sensors.ultrasonic.reading.return_value = reading

        self.assertEqual(
            self.car.distance(5),
            42.5,
        )
        self.assertIs(
            self.car.distance_reading(7),
            reading,
        )

        self.car.sensors.ultrasonic.distance.assert_called_once_with(5)
        self.car.sensors.ultrasonic.reading.assert_called_once_with(samples=7)

    def test_battery_methods_delegate(self) -> None:
        status = object()
        reading = object()

        self.car.sensors.battery.voltage.return_value = 7.8
        self.car.sensors.battery.is_low.return_value = True
        self.car.sensors.battery.is_critical.return_value = False
        self.car.sensors.battery.status.return_value = status
        self.car.sensors.battery.reading.return_value = reading

        self.assertEqual(
            self.car.battery_voltage(),
            7.8,
        )
        self.assertTrue(self.car.is_battery_low())
        self.assertFalse(self.car.is_battery_critical())
        self.assertIs(
            self.car.battery_status(),
            status,
        )
        self.assertIs(
            self.car.battery_reading(),
            reading,
        )

    def test_grayscale_methods_delegate(self) -> None:
        reading = object()

        self.car.sensors.grayscale.status.return_value = [
            0,
            1,
            0,
        ]
        self.car.sensors.grayscale.read.return_value = [
            100,
            500,
            110,
        ]
        self.car.sensors.grayscale.normalized.return_value = [
            0.1,
            0.9,
            0.2,
        ]
        self.car.sensors.grayscale.reading.return_value = reading

        self.assertEqual(
            self.car.line_status(threshold=0.4),
            [
                0,
                1,
                0,
            ],
        )
        self.assertEqual(
            self.car.line_values(),
            [
                100,
                500,
                110,
            ],
        )
        self.assertEqual(
            self.car.line_normalized(),
            [
                0.1,
                0.9,
                0.2,
            ],
        )
        self.assertIs(
            self.car.line_reading(threshold=0.6),
            reading,
        )

        self.car.sensors.grayscale.status.assert_called_once_with(threshold=0.4)
        self.car.sensors.grayscale.reading.assert_called_once_with(threshold=0.6)

    def test_sensors_status(self) -> None:
        expected = object()
        self.car.sensors.status.return_value = expected

        self.assertIs(
            self.car.sensors_status(),
            expected,
        )


class CarRobotVisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def test_vision_status_helpers(self) -> None:
        statistics = SimpleNamespace(
            running=True,
            recording=SimpleNamespace(active=True),
        )
        self.car.vision.statistics.return_value = statistics

        self.assertTrue(self.car.is_vision_running())
        self.assertTrue(self.car.is_recording())
        self.assertIs(
            self.car.vision_stats(),
            statistics,
        )

    def test_snapshot_delegates(self) -> None:
        expected = object()
        self.car.vision.snapshot.return_value = expected

        result = self.car.snapshot(
            filename="picture.jpg",
            overlay=True,
            source="color",
        )

        self.assertIs(
            result,
            expected,
        )
        self.car.vision.snapshot.assert_called_once_with(
            filename="picture.jpg",
            overlay=True,
            source="color",
        )

    def test_capture_is_snapshot_alias(self) -> None:
        expected = object()

        with patch.object(
            self.car,
            "snapshot",
            return_value=expected,
        ) as snapshot:
            result = self.car.capture(
                filename="picture.jpg",
                overlay=True,
                source="face",
            )

        self.assertIs(
            result,
            expected,
        )
        snapshot.assert_called_once_with(
            filename="picture.jpg",
            overlay=True,
            source="face",
        )

    def test_start_recording_tracks_ownership(
        self,
    ) -> None:
        path = Path("/tmp/video.mp4")
        self.car.vision.start_recording.return_value = path

        result = self.car.start_recording(
            filename="video.mp4",
            overlay=True,
            source="color",
        )

        self.assertEqual(
            result,
            path,
        )
        self.assertTrue(self.car._recording_started_by_robot)
        self.car.vision.start_recording.assert_called_once_with(
            filename="video.mp4",
            overlay=True,
            source="color",
        )

    def test_failed_start_recording_does_not_claim_ownership(
        self,
    ) -> None:
        self.car.vision.start_recording.side_effect = RuntimeError("failed")

        with self.assertRaisesRegex(
            RuntimeError,
            "failed",
        ):
            self.car.start_recording()

        self.assertFalse(self.car._recording_started_by_robot)

    def test_stop_recording_clears_ownership(
        self,
    ) -> None:
        expected = object()
        self.car._recording_started_by_robot = True
        self.car.vision.stop_recording.return_value = expected

        result = self.car.stop_recording()

        self.assertIs(
            result,
            expected,
        )
        self.assertFalse(self.car._recording_started_by_robot)

    def test_failed_stop_recording_preserves_ownership(
        self,
    ) -> None:
        self.car._recording_started_by_robot = True
        self.car.vision.stop_recording.side_effect = RuntimeError("failed")

        with self.assertRaisesRegex(
            RuntimeError,
            "failed",
        ):
            self.car.stop_recording()

        self.assertTrue(self.car._recording_started_by_robot)

    def test_detection_control_methods_delegate(
        self,
    ) -> None:
        enabled = object()
        colors = object()
        disabled = object()
        status = object()

        self.car.vision.enable_detection.return_value = enabled
        self.car.vision.enable_color_detection.return_value = colors
        self.car.vision.disable_detection.return_value = disabled
        self.car.vision.detection_status.return_value = status

        self.assertIs(
            self.car.enable_detection("face"),
            enabled,
        )
        self.assertIs(
            self.car.enable_color_detection(
                (
                    "red",
                    "blue",
                ),
                min_area=100,
            ),
            colors,
        )
        self.assertIs(
            self.car.disable_detection("face"),
            disabled,
        )
        self.assertIs(
            self.car.disable_color_detection(),
            disabled,
        )
        self.assertIs(
            self.car.detection_status(),
            status,
        )

        self.car.vision.enable_detection.assert_called_once_with("face")
        self.car.vision.enable_color_detection.assert_called_once_with(
            (
                "red",
                "blue",
            ),
            min_area=100,
        )
        self.assertEqual(
            self.car.vision.disable_detection.call_args_list,
            [
                call("face"),
                call("color"),
            ],
        )

    def test_stream_overlay_methods_delegate(
        self,
    ) -> None:
        enabled = object()
        disabled = object()

        self.car.vision.enable_stream_overlay.return_value = enabled
        self.car.vision.disable_stream_overlay.return_value = disabled

        self.assertIs(
            self.car.enable_stream_overlay("color"),
            enabled,
        )
        self.assertIs(
            self.car.disable_stream_overlay(),
            disabled,
        )


class CarRobotDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def set_metadata(
        self,
        detections: list[object],
    ) -> None:
        self.car.vision.metadata.return_value = SimpleNamespace(detections=detections)

    def test_metadata_none_produces_no_detections(
        self,
    ) -> None:
        self.car.vision.metadata.return_value = None

        self.assertEqual(
            self.car._detections("color"),
            [],
        )

    def test_detections_filter_label_case_insensitively(
        self,
    ) -> None:
        red = make_detection(
            label="Red",
            area=100,
        )
        blue = make_detection(
            label="blue",
            area=50,
        )
        self.set_metadata(
            [
                red,
                blue,
            ]
        )

        self.assertEqual(
            self.car._detections(
                "color",
                label=" red ",
            ),
            [
                red,
            ],
        )

    def test_detections_reject_blank_source(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "source cannot be empty",
        ):
            self.car._detections(" ")

    def test_detections_reject_blank_label(
        self,
    ) -> None:
        self.set_metadata([])

        with self.assertRaisesRegex(
            ValueError,
            "label cannot be empty",
        ):
            self.car._detections(
                "color",
                label=" ",
            )

    def test_color_helpers(self) -> None:
        small_red = make_detection(
            label="red",
            area=25,
            center=(
                10,
                20,
            ),
        )
        large_red = make_detection(
            label="red",
            area=100,
            center=(
                30,
                40,
            ),
        )
        blue = make_detection(
            label="blue",
            area=50,
            center=(
                50,
                60,
            ),
        )
        self.set_metadata(
            [
                small_red,
                large_red,
                blue,
            ]
        )

        self.assertTrue(self.car.sees_color("red"))
        self.assertEqual(
            self.car.color_count("red"),
            2,
        )
        self.assertEqual(
            self.car.visible_colors(),
            [
                "blue",
                "red",
            ],
        )
        self.assertIs(
            self.car.largest_color("red"),
            large_red,
        )
        self.assertEqual(
            self.car.color_center("red"),
            (
                30,
                40,
            ),
        )
        self.assertEqual(
            self.car.color_area("red"),
            100.0,
        )

    def test_color_helpers_when_missing(
        self,
    ) -> None:
        self.set_metadata([])

        self.assertFalse(self.car.sees_color("red"))
        self.assertEqual(
            self.car.color_count("red"),
            0,
        )
        self.assertIsNone(self.car.largest_color("red"))
        self.assertIsNone(self.car.color_center("red"))
        self.assertIsNone(self.car.color_area("red"))

    def test_largest_color_handles_invalid_area(
        self,
    ) -> None:
        invalid = make_detection(
            label="red",
            area="invalid",
        )
        valid = make_detection(
            label="red",
            area=10,
        )
        self.set_metadata(
            [
                invalid,
                valid,
            ]
        )

        self.assertIs(
            self.car.largest_color("red"),
            valid,
        )

    def test_face_helpers(self) -> None:
        small = make_detection(
            label="face",
            center=(
                10,
                20,
            ),
            box=(
                0,
                0,
                10,
                10,
            ),
        )
        large = make_detection(
            label="face",
            center=(
                30,
                40,
            ),
            box=(
                0,
                0,
                20,
                30,
            ),
        )
        no_center = make_detection(
            label="face",
            center=None,
            box=None,
        )
        self.set_metadata(
            [
                small,
                large,
                no_center,
            ]
        )

        self.assertTrue(self.car.sees_face())
        self.assertEqual(
            self.car.face_count(),
            3,
        )
        self.assertIs(
            self.car.largest_face(),
            large,
        )
        self.assertEqual(
            self.car.face_center(),
            (
                30,
                40,
            ),
        )
        self.assertEqual(
            self.car.face_centers(),
            [
                (
                    10,
                    20,
                ),
                (
                    30,
                    40,
                ),
            ],
        )

    def test_face_helpers_when_missing(
        self,
    ) -> None:
        self.set_metadata([])

        self.assertFalse(self.car.sees_face())
        self.assertEqual(
            self.car.face_count(),
            0,
        )
        self.assertIsNone(self.car.largest_face())
        self.assertIsNone(self.car.face_center())
        self.assertEqual(
            self.car.face_centers(),
            [],
        )


class CarRobotSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def test_system_methods_delegate(self) -> None:
        paths = MediaPaths(
            pictures=Path("/media/pictures"),
            videos=Path("/media/videos"),
            sounds=Path("/media/sounds"),
        )
        status = object()
        health = SystemHealth(
            ok=True,
            messages=(),
        )

        self.car.system.hostname.return_value = "Betabox-1234"
        self.car.system.ip_addresses.return_value = ("192.168.1.10",)
        self.car.system.media_paths.return_value = paths
        self.car.system.ensure_media_paths.return_value = paths
        self.car.system.status.return_value = status
        self.car.system.health.return_value = health

        self.assertEqual(
            self.car.hostname(),
            "Betabox-1234",
        )
        self.assertEqual(
            self.car.ip_addresses(),
            ("192.168.1.10",),
        )
        self.assertIs(
            self.car.media_paths(),
            paths,
        )
        self.assertIs(
            self.car.ensure_media_paths(),
            paths,
        )
        self.assertIs(
            self.car.status(),
            status,
        )
        self.assertIs(
            self.car.system_status(),
            status,
        )
        self.assertIs(
            self.car.system_health(),
            health,
        )

    def test_healthy_robot_health(self) -> None:
        self.car.system.health.return_value = SystemHealth(
            ok=True,
            messages=(),
        )
        self.car.sensors.battery.is_critical.return_value = False
        self.car.sensors.battery.status.return_value = SimpleNamespace(value="ok")

        health = self.car.health()

        self.assertIsInstance(
            health,
            RobotHealth,
        )
        self.assertTrue(health.ok)
        self.assertEqual(
            health.messages,
            (),
        )
        self.assertEqual(
            tuple(check.name for check in health.checks),
            (
                "system",
                "battery",
            ),
        )

    def test_unhealthy_robot_health(self) -> None:
        self.car.system.health.return_value = SystemHealth(
            ok=False,
            messages=(
                "missing media",
                "network unavailable",
            ),
        )
        self.car.sensors.battery.is_critical.return_value = True
        self.car.sensors.battery.status.return_value = SimpleNamespace(value="critical")

        health = self.car.health()

        self.assertFalse(health.ok)
        self.assertEqual(
            health.messages,
            (
                "missing media; network unavailable",
                "battery status: critical",
            ),
        )


class CarRobotShutdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.car = TestCar()
        self.car.start()

    def test_stop_all_stops_subsystems(
        self,
    ) -> None:
        self.car._recording_started_by_robot = True

        self.car.stop_all()

        self.car.vision.stop_recording.assert_called_once_with()
        self.car.drive.stop.assert_called_once_with()
        self.car.audio.stop.assert_called_once_with()
        self.car.system.stop_all.assert_called_once_with()

        self.assertFalse(self.car._recording_started_by_robot)
        self.assertFalse(self.car.started)
        self.assertFalse(self.car.closed)

    def test_stop_all_does_not_stop_unowned_recording(
        self,
    ) -> None:
        self.car._recording_started_by_robot = False

        self.car.stop_all()

        self.car.vision.stop_recording.assert_not_called()

    def test_stop_all_logs_and_continues_after_failures(
        self,
    ) -> None:
        self.car._recording_started_by_robot = True

        self.car.vision.stop_recording.side_effect = RuntimeError("recording failed")
        self.car.drive.stop.side_effect = RuntimeError("drive failed")
        self.car.audio.stop.side_effect = RuntimeError("audio failed")
        self.car.system.stop_all.side_effect = RuntimeError("system failed")

        with patch("betabox_robotics.robots.car.logger.exception") as log:
            self.car.stop_all()

        self.assertEqual(
            log.call_args_list,
            [
                call("Failed to stop robot-started recording."),
                call("Failed to stop drive subsystem."),
                call("Failed to stop audio subsystem."),
                call("Failed to stop system subsystem."),
            ],
        )
        self.assertFalse(self.car._recording_started_by_robot)
        self.assertFalse(self.car.started)

    def test_close_completes_despite_subsystem_failures(
        self,
    ) -> None:
        self.car.drive.stop.side_effect = RuntimeError("drive failed")
        self.car.audio.stop.side_effect = RuntimeError("audio failed")

        with patch("betabox_robotics.robots.car.logger.exception"):
            self.car.close()

        self.assertTrue(self.car.closed)
        self.assertFalse(self.car.started)

    def test_stop_all_rejects_closed_robot(
        self,
    ) -> None:
        self.car.close()

        with self.assertRaisesRegex(
            RobotLifecycleError,
            "robot is closed",
        ):
            self.car.stop_all()


if __name__ == "__main__":
    unittest.main()
