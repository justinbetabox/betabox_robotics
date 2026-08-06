from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
)
from betabox_robotics.services.hardware_checks import (
    AudioStatus,
    BatteryStatus,
    I2CStatus,
    RobotHardwareStatus,
    SensorStatus,
    VisionStatus,
)
from betabox_robotics.services.hardware_status import (
    _validate_config,
    _validate_robot_config,
    collect_hardware_status,
    main,
)

MODULE = "betabox_robotics.services.hardware_status"


def make_i2c_status() -> I2CStatus:
    return I2CStatus(
        available=True,
        devices=(
            "0x14",
            "0x40",
        ),
    )


def make_audio_status() -> AudioStatus:
    return AudioStatus(
        available=True,
        device="HifiBerry DAC",
    )


def make_vision_status() -> VisionStatus:
    return VisionStatus(
        service_available=True,
        running=True,
        camera_running=True,
        camera_has_frame=True,
        clients=1,
    )


def make_battery_status() -> BatteryStatus:
    return BatteryStatus(
        available=True,
        voltage=8.2,
        state="ok",
    )


def make_sensor_status() -> SensorStatus:
    return SensorStatus(
        grayscale_available=True,
        grayscale_values=(
            100,
            200,
            300,
        ),
        ultrasonic_configured=True,
    )


class ValidateConfigTests(unittest.TestCase):
    def test_accepts_platform_config(self) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_rejects_invalid_config(self) -> None:
        for value in (
            None,
            object(),
            "config",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "config must be a PlatformConfig",
                ),
            ):
                _validate_config(value)


class ValidateRobotConfigTests(unittest.TestCase):
    def test_accepts_robot_config(self) -> None:
        result = _validate_robot_config(BETABOX_CAR)

        self.assertIs(
            result,
            BETABOX_CAR,
        )

    def test_rejects_invalid_robot_config(self) -> None:
        for value in (
            None,
            object(),
            "robot",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("robot_config must be a RobotConfig"),
                ),
            ):
                _validate_robot_config(value)


class CollectHardwareStatusTests(unittest.TestCase):
    def test_collects_complete_hardware_status(self) -> None:
        i2c = make_i2c_status()
        audio = make_audio_status()
        vision = make_vision_status()
        battery = make_battery_status()
        sensors = make_sensor_status()

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=i2c,
            ) as collect_i2c,
            patch(
                f"{MODULE}.collect_audio_status",
                return_value=audio,
            ) as collect_audio,
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=vision,
            ) as collect_vision,
            patch(
                f"{MODULE}.collect_robot_status",
                return_value=(
                    True,
                    battery,
                    sensors,
                    None,
                ),
            ) as collect_robot,
        ):
            status = collect_hardware_status()

        self.assertEqual(
            status,
            RobotHardwareStatus(
                i2c=i2c,
                passive_hardware_available=True,
                battery=battery,
                sensors=sensors,
                audio=audio,
                vision=vision,
                passive_hardware_error=None,
            ),
        )

        collect_i2c.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_audio.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_vision.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_robot.assert_called_once_with(BETABOX_CAR.sensors)

    def test_uses_supplied_platform_config(self) -> None:
        i2c = make_i2c_status()
        audio = make_audio_status()
        vision = make_vision_status()
        battery = make_battery_status()
        sensors = make_sensor_status()

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=i2c,
            ) as collect_i2c,
            patch(
                f"{MODULE}.collect_audio_status",
                return_value=audio,
            ) as collect_audio,
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=vision,
            ) as collect_vision,
            patch(
                f"{MODULE}.collect_robot_status",
                return_value=(
                    True,
                    battery,
                    sensors,
                    None,
                ),
            ),
        ):
            collect_hardware_status(DEFAULT_PLATFORM_CONFIG)

        collect_i2c.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_audio.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_vision.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)

    def test_uses_injected_robot_config(self) -> None:
        i2c = make_i2c_status()
        audio = make_audio_status()
        vision = make_vision_status()
        battery = make_battery_status()
        sensors = make_sensor_status()

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=i2c,
            ),
            patch(
                f"{MODULE}.collect_audio_status",
                return_value=audio,
            ),
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=vision,
            ),
            patch(
                f"{MODULE}.collect_robot_status",
                return_value=(
                    True,
                    battery,
                    sensors,
                    None,
                ),
            ) as collect_robot,
        ):
            collect_hardware_status(robot_config=BETABOX_CAR)

        collect_robot.assert_called_once_with(BETABOX_CAR.sensors)

    def test_preserves_passive_hardware_failure(
        self,
    ) -> None:
        i2c = make_i2c_status()
        audio = make_audio_status()
        vision = make_vision_status()
        battery = BatteryStatus(
            available=False,
            voltage=None,
            state="unknown",
            error="battery failed",
        )
        sensors = make_sensor_status()

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=i2c,
            ),
            patch(
                f"{MODULE}.collect_audio_status",
                return_value=audio,
            ),
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=vision,
            ),
            patch(
                f"{MODULE}.collect_robot_status",
                return_value=(
                    False,
                    battery,
                    sensors,
                    "battery failed",
                ),
            ),
        ):
            status = collect_hardware_status()

        self.assertFalse(status.passive_hardware_available)
        self.assertEqual(
            status.passive_hardware_error,
            "battery failed",
        )
        self.assertIs(
            status.battery,
            battery,
        )
        self.assertIs(
            status.sensors,
            sensors,
        )

    def test_validates_platform_config_before_collectors(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.collect_i2c_status") as collect_i2c,
            patch(f"{MODULE}.collect_audio_status") as collect_audio,
            patch(f"{MODULE}.collect_vision_status") as collect_vision,
            patch(f"{MODULE}.collect_robot_status") as collect_robot,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_hardware_status(
                object(),  # type: ignore[arg-type]
            )

        collect_i2c.assert_not_called()
        collect_audio.assert_not_called()
        collect_vision.assert_not_called()
        collect_robot.assert_not_called()

    def test_validates_robot_config_before_collectors(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.collect_i2c_status") as collect_i2c,
            patch(f"{MODULE}.collect_audio_status") as collect_audio,
            patch(f"{MODULE}.collect_vision_status") as collect_vision,
            patch(f"{MODULE}.collect_robot_status") as collect_robot,
            self.assertRaisesRegex(
                TypeError,
                ("robot_config must be a RobotConfig"),
            ),
        ):
            collect_hardware_status(
                robot_config=object(),  # type: ignore[arg-type]
            )

        collect_i2c.assert_not_called()
        collect_audio.assert_not_called()
        collect_vision.assert_not_called()
        collect_robot.assert_not_called()

    def test_i2c_error_propagates(self) -> None:
        error = RuntimeError("i2c collector failed")

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_hardware_status()

        self.assertIs(
            context.exception,
            error,
        )

    def test_audio_error_propagates(self) -> None:
        error = RuntimeError("audio collector failed")

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=make_i2c_status(),
            ),
            patch(
                f"{MODULE}.collect_audio_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_hardware_status()

        self.assertIs(
            context.exception,
            error,
        )

    def test_vision_error_propagates(self) -> None:
        error = RuntimeError("vision collector failed")

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=make_i2c_status(),
            ),
            patch(
                f"{MODULE}.collect_audio_status",
                return_value=make_audio_status(),
            ),
            patch(
                f"{MODULE}.collect_vision_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_hardware_status()

        self.assertIs(
            context.exception,
            error,
        )

    def test_passive_error_propagates(self) -> None:
        error = RuntimeError("passive collector failed")

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=make_i2c_status(),
            ),
            patch(
                f"{MODULE}.collect_audio_status",
                return_value=make_audio_status(),
            ),
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=make_vision_status(),
            ),
            patch(
                f"{MODULE}.collect_robot_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_hardware_status()

        self.assertIs(
            context.exception,
            error,
        )

    def test_collectors_run_in_expected_order(self) -> None:
        parent = Mock()

        i2c = make_i2c_status()
        audio = make_audio_status()
        vision = make_vision_status()
        battery = make_battery_status()
        sensors = make_sensor_status()

        with (
            patch(
                f"{MODULE}.collect_i2c_status",
                return_value=i2c,
            ) as collect_i2c,
            patch(
                f"{MODULE}.collect_audio_status",
                return_value=audio,
            ) as collect_audio,
            patch(
                f"{MODULE}.collect_vision_status",
                return_value=vision,
            ) as collect_vision,
            patch(
                f"{MODULE}.collect_robot_status",
                return_value=(
                    True,
                    battery,
                    sensors,
                    None,
                ),
            ) as collect_robot,
        ):
            parent.attach_mock(
                collect_i2c,
                "i2c",
            )
            parent.attach_mock(
                collect_audio,
                "audio",
            )
            parent.attach_mock(
                collect_vision,
                "vision",
            )
            parent.attach_mock(
                collect_robot,
                "robot",
            )

            collect_hardware_status()

        self.assertEqual(
            parent.mock_calls,
            [
                call.i2c(DEFAULT_PLATFORM_CONFIG),
                call.audio(DEFAULT_PLATFORM_CONFIG),
                call.vision(DEFAULT_PLATFORM_CONFIG),
                call.robot(BETABOX_CAR.sensors),
            ],
        )


class MainTests(unittest.TestCase):
    def test_prints_json_status(self) -> None:
        status = RobotHardwareStatus(
            i2c=make_i2c_status(),
            passive_hardware_available=True,
            battery=make_battery_status(),
            sensors=make_sensor_status(),
            audio=make_audio_status(),
            vision=make_vision_status(),
        )

        with (
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=status,
            ) as collect,
            patch("builtins.print") as print_message,
        ):
            result = main()

        self.assertEqual(
            result,
            0,
        )
        collect.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        print_message.assert_called_once_with(
            json.dumps(
                status.to_dict(),
                indent=2,
            )
        )

    def test_printed_status_is_valid_json(self) -> None:
        status = RobotHardwareStatus(
            i2c=make_i2c_status(),
            passive_hardware_available=True,
            battery=make_battery_status(),
            sensors=make_sensor_status(),
            audio=make_audio_status(),
            vision=make_vision_status(),
        )

        printed: list[str] = []

        with (
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=status,
            ),
            patch(
                "builtins.print",
                side_effect=printed.append,
            ),
        ):
            result = main()

        self.assertEqual(
            result,
            0,
        )
        self.assertEqual(
            len(printed),
            1,
        )
        self.assertEqual(
            json.loads(printed[0]),
            status.to_dict(),
        )

    def test_collection_error_propagates(self) -> None:
        error = RuntimeError("hardware collection failed")

        with (
            patch(
                f"{MODULE}.collect_hardware_status",
                side_effect=error,
            ),
            patch("builtins.print") as print_message,
            self.assertRaises(RuntimeError) as context,
        ):
            main()

        self.assertIs(
            context.exception,
            error,
        )
        print_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
