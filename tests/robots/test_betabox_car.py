from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from gpiozero.exc import GPIOPinInUse

from betabox_robotics.calibration import (
    CameraMountCalibration,
    GrayscaleCalibration,
    MotorCalibration,
    RobotCalibration,
    SteeringCalibration,
)
from betabox_robotics.exceptions import RobotBusyError
from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
    BetaboxCar,
)
from betabox_robotics.robots.car import CarRobot
from betabox_robotics.robots.config import RobotConfig

MODULE = "betabox_robotics.robots.betabox_car"


def make_subsystem() -> MagicMock:
    subsystem = MagicMock()
    subsystem.close = MagicMock()
    return subsystem


class BetaboxCarConstructionTests(unittest.TestCase):
    def test_is_car_robot(self) -> None:
        self.assertTrue(
            issubclass(
                BetaboxCar,
                CarRobot,
            )
        )

    def test_default_config_is_robot_config(self) -> None:
        self.assertIsInstance(
            BETABOX_CAR,
            RobotConfig,
        )

    def test_rejects_invalid_config_before_ownership(self) -> None:
        with (
            patch(f"{MODULE}.RobotOwnership") as ownership_type,
            self.assertRaisesRegex(
                TypeError,
                "config must be a RobotConfig",
            ),
        ):
            BetaboxCar(
                config=object(),  # type: ignore[arg-type]
            )

        ownership_type.assert_not_called()

    def test_rejects_invalid_calibration_before_ownership(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.RobotOwnership") as ownership_type,
            self.assertRaisesRegex(
                TypeError,
                "calibration must be a RobotCalibration",
            ),
        ):
            BetaboxCar(
                calibration=object(),  # type: ignore[arg-type]
            )

        ownership_type.assert_not_called()

    def test_constructs_default_subsystems(self) -> None:
        ownership = MagicMock()
        drive = make_subsystem()
        sensors = make_subsystem()
        camera_mount = make_subsystem()
        vision = make_subsystem()
        audio = make_subsystem()
        system = make_subsystem()

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ) as ownership_type,
            patch(
                f"{MODULE}.Drive.default",
                return_value=drive,
            ) as drive_default,
            patch(
                f"{MODULE}.Sensors.default",
                return_value=sensors,
            ) as sensors_default,
            patch(
                f"{MODULE}.CameraMount.default",
                return_value=camera_mount,
            ) as camera_default,
            patch(
                f"{MODULE}.VisionClient.default",
                return_value=vision,
            ) as vision_default,
            patch(
                f"{MODULE}.Audio.default",
                return_value=audio,
            ) as audio_default,
            patch(
                f"{MODULE}.System.default",
                return_value=system,
            ) as system_default,
        ):
            car = BetaboxCar(owner="Test application")

        ownership_type.assert_called_once_with(owner="Test application")
        ownership.acquire.assert_called_once_with()

        drive_default.assert_called_once_with(
            BETABOX_CAR.drive,
            left_trim=1.0,
            right_trim=1.0,
            steering_offset=0.0,
        )
        sensors_default.assert_called_once_with(BETABOX_CAR.sensors)
        camera_default.assert_called_once_with(
            BETABOX_CAR.camera_mount,
            pan_offset=0.0,
            tilt_offset=0.0,
        )
        vision_default.assert_called_once_with(BETABOX_CAR.vision)
        audio_default.assert_called_once_with(BETABOX_CAR.audio)
        system_default.assert_called_once_with(BETABOX_CAR.system)

        self.assertIs(
            car.config,
            BETABOX_CAR,
        )
        self.assertEqual(
            car.calibration,
            RobotCalibration.default(),
        )
        self.assertIs(car.drive, drive)
        self.assertIs(car.sensors, sensors)
        self.assertIs(
            car.camera_mount,
            camera_mount,
        )
        self.assertIs(car.vision, vision)
        self.assertIs(car.audio, audio)
        self.assertIs(car.system, system)
        self.assertTrue(car.started)
        self.assertFalse(car.closed)

    def test_applies_saved_calibration(self) -> None:
        ownership = MagicMock()
        drive = make_subsystem()
        sensors = make_subsystem()
        sensors.grayscale = MagicMock()
        camera_mount = make_subsystem()

        calibration = RobotCalibration(
            motors=MotorCalibration(
                left_trim=0.8,
                right_trim=0.9,
            ),
            steering=SteeringCalibration(
                offset=4.0,
            ),
            camera_mount=CameraMountCalibration(
                pan_offset=3.0,
                tilt_offset=-2.0,
            ),
            grayscale=GrayscaleCalibration(
                floor=(
                    100.0,
                    110.0,
                    120.0,
                ),
                line=(
                    500.0,
                    510.0,
                    520.0,
                ),
            ),
        )

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                f"{MODULE}.Drive.default",
                return_value=drive,
            ) as drive_default,
            patch(
                f"{MODULE}.Sensors.default",
                return_value=sensors,
            ),
            patch(
                f"{MODULE}.CameraMount.default",
                return_value=camera_mount,
            ) as camera_default,
            patch(
                f"{MODULE}.VisionClient.default",
                return_value=make_subsystem(),
            ),
            patch(
                f"{MODULE}.Audio.default",
                return_value=make_subsystem(),
            ),
            patch(
                f"{MODULE}.System.default",
                return_value=make_subsystem(),
            ),
        ):
            car = BetaboxCar(calibration=calibration)

        self.assertIs(
            car.calibration,
            calibration,
        )

        drive_default.assert_called_once_with(
            BETABOX_CAR.drive,
            left_trim=0.8,
            right_trim=0.9,
            steering_offset=4.0,
        )
        camera_default.assert_called_once_with(
            BETABOX_CAR.camera_mount,
            pan_offset=3.0,
            tilt_offset=-2.0,
        )
        sensors.grayscale.set_calibration.assert_called_once_with(
            (
                100.0,
                110.0,
                120.0,
            ),
            (
                500.0,
                510.0,
                520.0,
            ),
        )

    def test_default_grayscale_calibration_is_not_applied(
        self,
    ) -> None:
        ownership = MagicMock()
        sensors = make_subsystem()
        sensors.grayscale = MagicMock()

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                f"{MODULE}.Drive.default",
                return_value=make_subsystem(),
            ),
            patch(
                f"{MODULE}.Sensors.default",
                return_value=sensors,
            ),
            patch(
                f"{MODULE}.CameraMount.default",
                return_value=make_subsystem(),
            ),
            patch(
                f"{MODULE}.VisionClient.default",
                return_value=make_subsystem(),
            ),
            patch(
                f"{MODULE}.Audio.default",
                return_value=make_subsystem(),
            ),
            patch(
                f"{MODULE}.System.default",
                return_value=make_subsystem(),
            ),
        ):
            BetaboxCar()

        sensors.grayscale.set_calibration.assert_not_called()


class BetaboxCarRollbackTests(unittest.TestCase):
    def test_failed_ownership_acquisition_does_not_cleanup(
        self,
    ) -> None:
        ownership = MagicMock()
        acquisition_error = RobotBusyError("already owned")
        ownership.acquire.side_effect = acquisition_error

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(f"{MODULE}.close_gpio_factory") as close_factory,
            patch(f"{MODULE}.Drive.default") as drive_default,
            self.assertRaises(RobotBusyError) as context,
        ):
            BetaboxCar()

        self.assertIs(
            context.exception,
            acquisition_error,
        )
        drive_default.assert_not_called()
        close_factory.assert_not_called()
        ownership.release.assert_not_called()

    def test_gpio_conflict_is_wrapped_and_rolls_back(
        self,
    ) -> None:
        ownership = MagicMock()
        pin_error = GPIOPinInUse(4)

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                f"{MODULE}.Drive.default",
                side_effect=pin_error,
            ),
            self.assertRaisesRegex(
                RobotBusyError,
                "hardware could not be acquired",
            ) as context,
        ):
            BetaboxCar()

        self.assertIs(
            context.exception.__cause__,
            pin_error,
        )
        ownership.release.assert_called_once_with()

    def test_constructor_failure_closes_created_subsystems(
        self,
    ) -> None:
        ownership = MagicMock()
        drive = make_subsystem()
        sensors = make_subsystem()
        camera_mount = make_subsystem()
        construction_error = RuntimeError("vision failed")

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                f"{MODULE}.Drive.default",
                return_value=drive,
            ),
            patch(
                f"{MODULE}.Sensors.default",
                return_value=sensors,
            ),
            patch(
                f"{MODULE}.CameraMount.default",
                return_value=camera_mount,
            ),
            patch(
                f"{MODULE}.VisionClient.default",
                side_effect=construction_error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            BetaboxCar()

        self.assertIs(
            context.exception,
            construction_error,
        )
        camera_mount.close.assert_called_once_with()
        drive.close.assert_called_once_with()
        sensors.close.assert_called_once_with()
        ownership.release.assert_called_once_with()

    def test_constructor_failure_does_not_close_uncreated_subsystems(
        self,
    ) -> None:
        ownership = MagicMock()
        drive = make_subsystem()
        construction_error = RuntimeError("sensors failed")

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                f"{MODULE}.Drive.default",
                return_value=drive,
            ),
            patch(
                f"{MODULE}.Sensors.default",
                side_effect=construction_error,
            ),
            patch(f"{MODULE}.logger.exception") as log,
            self.assertRaises(RuntimeError),
        ):
            BetaboxCar()

        drive.close.assert_called_once_with()
        ownership.release.assert_called_once_with()
        log.assert_not_called()

    def test_close_failure_during_rollback_is_logged(
        self,
    ) -> None:
        ownership = MagicMock()
        drive = make_subsystem()
        drive.close.side_effect = RuntimeError("drive close failed")

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                f"{MODULE}.Drive.default",
                return_value=drive,
            ),
            patch(
                f"{MODULE}.Sensors.default",
                side_effect=RuntimeError("sensors failed"),
            ),
            patch(f"{MODULE}.logger.exception") as log,
            self.assertRaisesRegex(
                RuntimeError,
                "sensors failed",
            ),
        ):
            BetaboxCar()

        log.assert_called_once_with(
            "Failed to close %s subsystem.",
            "drive",
        )
        ownership.release.assert_called_once_with()


class BetaboxCarCloseTests(unittest.TestCase):
    def make_car(
        self,
    ) -> tuple[
        BetaboxCar,
        MagicMock,
        dict[str, MagicMock],
    ]:
        ownership = MagicMock()

        subsystems = {
            "drive": make_subsystem(),
            "sensors": make_subsystem(),
            "camera_mount": make_subsystem(),
            "vision": make_subsystem(),
            "audio": make_subsystem(),
            "system": make_subsystem(),
        }

        with (
            patch(
                f"{MODULE}.RobotOwnership",
                return_value=ownership,
            ),
            patch(
                f"{MODULE}.Drive.default",
                return_value=subsystems["drive"],
            ),
            patch(
                f"{MODULE}.Sensors.default",
                return_value=subsystems["sensors"],
            ),
            patch(
                f"{MODULE}.CameraMount.default",
                return_value=subsystems["camera_mount"],
            ),
            patch(
                f"{MODULE}.VisionClient.default",
                return_value=subsystems["vision"],
            ),
            patch(
                f"{MODULE}.Audio.default",
                return_value=subsystems["audio"],
            ),
            patch(
                f"{MODULE}.System.default",
                return_value=subsystems["system"],
            ),
        ):
            car = BetaboxCar()

        return (
            car,
            ownership,
            subsystems,
        )

    def test_close_stops_closes_gpio_and_releases(
        self,
    ) -> None:
        car, ownership, subsystems = self.make_car()

        with (
            patch.object(car, "stop_all") as stop_all,
            patch(f"{MODULE}.close_gpio_factory") as close_factory,
        ):
            car.close()

        stop_all.assert_called_once_with()

        for subsystem in subsystems.values():
            subsystem.close.assert_called_once_with()

        close_factory.assert_called_once_with()
        ownership.release.assert_called_once_with()
        self.assertFalse(car.started)
        self.assertTrue(car.closed)

    def test_close_is_idempotent(self) -> None:
        car, ownership, _ = self.make_car()

        with (
            patch.object(car, "stop_all") as stop_all,
            patch.object(car, "_close_constructed_subsystems") as close_subsystems,
            patch(f"{MODULE}.close_gpio_factory") as close_factory,
        ):
            car.close()
            car.close()

        stop_all.assert_called_once_with()
        close_subsystems.assert_called_once_with()
        close_factory.assert_called_once_with()
        ownership.release.assert_called_once_with()

    def test_close_completes_when_stop_all_fails(
        self,
    ) -> None:
        car, ownership, subsystems = self.make_car()

        stop_error = RuntimeError("stop failed")

        with (
            patch.object(
                car,
                "stop_all",
                side_effect=stop_error,
            ),
            patch(f"{MODULE}.close_gpio_factory") as close_factory,
            self.assertRaises(RuntimeError) as context,
        ):
            car.close()

        self.assertIs(
            context.exception,
            stop_error,
        )

        for subsystem in subsystems.values():
            subsystem.close.assert_called_once_with()

        close_factory.assert_called_once_with()
        ownership.release.assert_called_once_with()
        self.assertFalse(car.started)
        self.assertTrue(car.closed)

    def test_close_releases_when_gpio_cleanup_fails(
        self,
    ) -> None:
        car, ownership, _ = self.make_car()
        cleanup_error = RuntimeError("GPIO cleanup failed")

        with (
            patch.object(car, "stop_all"),
            patch(
                f"{MODULE}.close_gpio_factory",
                side_effect=cleanup_error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            car.close()

        self.assertIs(
            context.exception,
            cleanup_error,
        )
        ownership.release.assert_called_once_with()
        self.assertTrue(car.closed)

    def test_subsystem_close_failures_are_logged_and_ignored(
        self,
    ) -> None:
        car, _, subsystems = self.make_car()

        subsystems["vision"].close.side_effect = RuntimeError("vision failed")
        subsystems["drive"].close.side_effect = RuntimeError("drive failed")

        with (
            patch.object(car, "stop_all"),
            patch(f"{MODULE}.close_gpio_factory"),
            patch(f"{MODULE}.logger.exception") as log,
        ):
            car.close()

        self.assertEqual(
            log.call_args_list,
            [
                call(
                    "Failed to close %s subsystem.",
                    "vision",
                ),
                call(
                    "Failed to close %s subsystem.",
                    "drive",
                ),
            ],
        )
        self.assertTrue(car.closed)

    def test_context_manager_closes_car(self) -> None:
        car, ownership, _ = self.make_car()

        with (
            patch.object(car, "stop_all"),
            patch(f"{MODULE}.close_gpio_factory"),
            car as active,
        ):
            self.assertIs(
                active,
                car,
            )
            self.assertTrue(car.started)

        ownership.release.assert_called_once_with()
        self.assertTrue(car.closed)


class BetaboxCarSubsystemCleanupTests(unittest.TestCase):
    def test_cleanup_uses_expected_reverse_dependency_order(
        self,
    ) -> None:
        car = object.__new__(BetaboxCar)

        manager = MagicMock()

        car.vision = MagicMock()
        car.audio = MagicMock()
        car.camera_mount = MagicMock()
        car.drive = MagicMock()
        car.sensors = MagicMock()
        car.system = MagicMock()

        for name in (
            "vision",
            "audio",
            "camera_mount",
            "drive",
            "sensors",
            "system",
        ):
            subsystem = getattr(
                car,
                name,
            )
            subsystem.close.side_effect = lambda current=name: manager(current)

        car._close_constructed_subsystems()

        self.assertEqual(
            manager.call_args_list,
            [
                call("vision"),
                call("audio"),
                call("camera_mount"),
                call("drive"),
                call("sensors"),
                call("system"),
            ],
        )

    def test_cleanup_handles_partially_constructed_instance(
        self,
    ) -> None:
        car = object.__new__(BetaboxCar)
        car.drive = make_subsystem()

        car._close_constructed_subsystems()

        car.drive.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
