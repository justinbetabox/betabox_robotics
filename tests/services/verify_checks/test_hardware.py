from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from betabox_robotics.hardware.exceptions import (
    HardwareError,
)
from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
)
from betabox_robotics.robots.exceptions import (
    RobotError,
)
from betabox_robotics.sensors.exceptions import (
    SensorError,
)
from betabox_robotics.services.hardware_checks import (
    AudioStatus,
    BatteryStatus,
    I2CStatus,
    RobotHardwareStatus,
    SensorStatus,
    VisionStatus,
)
from betabox_robotics.services.verify_checks.hardware import (
    _validate_robot_config,
    check_hifiberry,
    check_i2c_device,
    check_i2c_scan,
    check_robot_constructs,
    check_ultrasonic_read,
    checks_from_hardware_status,
)
from betabox_robotics.services.verify_checks.models import (
    CheckResult,
)

MODULE = "betabox_robotics.services.verify_checks.hardware"


def make_result(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def make_hardware_status(
    *,
    i2c_available: bool = True,
    i2c_devices: list[str] | None = None,
    i2c_error: str | None = None,
    passive_available: bool = True,
    passive_error: str | None = None,
    battery_available: bool = True,
    battery_voltage: float | None = 8.2,
    battery_state: str = "ok",
    battery_error: str | None = None,
    grayscale_available: bool = True,
    grayscale_values: list[float] | None = None,
    ultrasonic_configured: bool = True,
    sensor_error: str | None = None,
    audio_available: bool = True,
    audio_device: str | None = "HifiBerry DAC",
    audio_error: str | None = None,
    vision_service_available: bool = True,
    vision_running: bool = True,
    vision_camera_running: bool = True,
    vision_camera_has_frame: bool = True,
    vision_error: str | None = None,
) -> RobotHardwareStatus:
    return RobotHardwareStatus(
        i2c=I2CStatus(
            available=i2c_available,
            devices=(["0x14"] if i2c_devices is None else i2c_devices),
            error=i2c_error,
        ),
        passive_hardware_available=(passive_available),
        battery=BatteryStatus(
            available=battery_available,
            voltage=battery_voltage,
            state=battery_state,
            error=battery_error,
        ),
        sensors=SensorStatus(
            grayscale_available=(grayscale_available),
            grayscale_values=(
                [100.0, 200.0, 300.0] if grayscale_values is None else grayscale_values
            ),
            ultrasonic_configured=(ultrasonic_configured),
            error=sensor_error,
        ),
        audio=AudioStatus(
            available=audio_available,
            device=audio_device,
            error=audio_error,
        ),
        vision=VisionStatus(
            service_available=(vision_service_available),
            running=vision_running,
            camera_running=(vision_camera_running),
            camera_has_frame=(vision_camera_has_frame),
            clients=0,
            error=vision_error,
        ),
        passive_hardware_error=passive_error,
    )


class ValidateRobotConfigTests(unittest.TestCase):
    def test_accepts_robot_config(self) -> None:
        result = _validate_robot_config(BETABOX_CAR)

        self.assertIs(
            result,
            BETABOX_CAR,
        )

    def test_rejects_invalid_robot_config(
        self,
    ) -> None:
        for value in (
            None,
            object(),
            "robot",
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("robot_config must be a RobotConfig"),
                ),
            ):
                _validate_robot_config(value)


class CheckI2CDeviceTests(unittest.TestCase):
    def test_reports_existing_device(self) -> None:
        path = DEFAULT_I2C_PATH

        with patch.object(
            Path,
            "exists",
            return_value=True,
        ) as exists:
            result = check_i2c_device()

        exists.assert_called_once_with()
        self.assertEqual(
            result,
            CheckResult(
                name="hardware:i2c",
                ok=True,
                message=str(path),
            ),
        )

    def test_reports_missing_device(self) -> None:
        path = DEFAULT_I2C_PATH

        with patch.object(
            Path,
            "exists",
            return_value=False,
        ):
            result = check_i2c_device()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:i2c",
                ok=False,
                message=f"{path} missing",
            ),
        )

    def test_reports_filesystem_error(self) -> None:
        with patch.object(
            Path,
            "exists",
            side_effect=OSError("permission denied"),
        ):
            result = check_i2c_device()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:i2c",
                ok=False,
                message="permission denied",
            ),
        )

    def test_rejects_invalid_config_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            check_i2c_device(
                object()  # type: ignore[arg-type]
            )

        exists.assert_not_called()

    def test_unexpected_filesystem_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch.object(
                Path,
                "exists",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_i2c_device()

        self.assertIs(
            context.exception,
            error,
        )


class CheckI2CScanTests(unittest.TestCase):
    def test_reports_detected_device(self) -> None:
        verification = DEFAULT_VERIFICATION

        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("     0  1  2  3  4  5\n10: -- -- -- -- 14 --\n"),
            ),
        ) as run:
            result = check_i2c_scan()

        run.assert_called_once_with(
            [
                "i2cdetect",
                "-y",
                str(verification.i2c_bus),
            ],
            timeout=(verification.command_timeout_seconds),
        )
        self.assertEqual(
            result,
            CheckResult(
                name="hardware:i2cdetect",
                ok=True,
                message="I2C devices found",
            ),
        )

    def test_accepts_uppercase_hex_address(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="20: -- -- 3A --\n",
            ),
        ):
            result = check_i2c_scan()

        self.assertTrue(result.ok)

    def test_ignores_empty_addresses(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("     0  1  2  3\n00: -- -- -- --\n10: -- UU -- --\n"),
            ),
        ):
            result = check_i2c_scan()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:i2cdetect",
                ok=False,
                message=("no I2C devices found"),
            ),
        )

    def test_does_not_treat_row_header_as_device(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("     0  1  2  3\n00: -- -- -- --\n10: -- -- -- --\n"),
            ),
        ):
            result = check_i2c_scan()

        self.assertFalse(result.ok)

    def test_reports_command_cannot_run(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = check_i2c_scan()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:i2cdetect",
                ok=False,
                message=("i2cdetect failed to run"),
            ),
        )

    def test_failed_command_uses_stderr(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="permission denied\n",
            ),
        ):
            result = check_i2c_scan()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:i2cdetect",
                ok=False,
                message="permission denied",
            ),
        )

    def test_failed_command_uses_stdout_fallback(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="failed\n",
            ),
        ):
            result = check_i2c_scan()

        self.assertEqual(
            result.message,
            "failed",
        )

    def test_failed_command_without_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(returncode=1),
        ):
            result = check_i2c_scan()

        self.assertEqual(
            result.message,
            "i2cdetect failed",
        )

    def test_rejects_invalid_config_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            check_i2c_scan(
                object()  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_unexpected_runner_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.run",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_i2c_scan()

        self.assertIs(
            context.exception,
            error,
        )


class CheckHifiberryTests(unittest.TestCase):
    def test_reports_detected_hifiberry(
        self,
    ) -> None:
        verification = DEFAULT_VERIFICATION
        identifier = verification.hifiberry_identifiers[0]

        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=(f"card 0: {identifier} [device]\n"),
            ),
        ) as run:
            result = check_hifiberry()

        run.assert_called_once_with(
            [
                "aplay",
                "-l",
            ],
            timeout=(verification.command_timeout_seconds),
        )
        self.assertEqual(
            result,
            CheckResult(
                name="audio:hifiberry",
                ok=True,
                message="HifiBerry detected",
            ),
        )

    def test_searches_stderr_too(self) -> None:
        identifier = DEFAULT_VERIFICATION.hifiberry_identifiers[0]

        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stderr=identifier,
            ),
        ):
            result = check_hifiberry()

        self.assertTrue(result.ok)

    def test_reports_missing_hifiberry(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="card 0: Generic Audio\n",
            ),
        ):
            result = check_hifiberry()

        self.assertEqual(
            result,
            CheckResult(
                name="audio:hifiberry",
                ok=False,
                message=("HifiBerry not found in aplay -l"),
            ),
        )

    def test_reports_command_cannot_run(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = check_hifiberry()

        self.assertEqual(
            result,
            CheckResult(
                name="audio:hifiberry",
                ok=False,
                message="aplay failed to run",
            ),
        )

    def test_reports_failed_command(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stderr="audio unavailable\n",
            ),
        ):
            result = check_hifiberry()

        self.assertEqual(
            result,
            CheckResult(
                name="audio:hifiberry",
                ok=False,
                message="audio unavailable",
            ),
        )

    def test_failed_command_without_output(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(returncode=1),
        ):
            result = check_hifiberry()

        self.assertEqual(
            result.message,
            "aplay failed",
        )

    def test_rejects_invalid_config_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            check_hifiberry(
                object()  # type: ignore[arg-type]
            )

        run.assert_not_called()


class CheckRobotConstructsTests(unittest.TestCase):
    def test_constructs_and_closes_robot(self) -> None:
        car = Mock()

        with patch(
            "betabox_robotics.BetaboxCar",
            return_value=car,
        ) as betabox_car:
            result = check_robot_constructs()

        betabox_car.assert_called_once_with(BETABOX_CAR)
        car.close.assert_called_once_with()
        self.assertEqual(
            result,
            CheckResult(
                name="robot:construct",
                ok=True,
                message=("BetaboxCar constructed successfully"),
            ),
        )

    def test_reports_hardware_construction_error(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.BetaboxCar",
            side_effect=HardwareError("hardware unavailable"),
        ):
            result = check_robot_constructs()

        self.assertEqual(
            result,
            CheckResult(
                name="robot:construct",
                ok=False,
                message="hardware unavailable",
            ),
        )

    def test_reports_robot_construction_error(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.BetaboxCar",
            side_effect=RobotError("robot failed"),
        ):
            result = check_robot_constructs()

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "robot failed",
        )

    def test_reports_os_construction_error(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.BetaboxCar",
            side_effect=OSError("device missing"),
        ):
            result = check_robot_constructs()

        self.assertFalse(result.ok)
        self.assertEqual(
            result.message,
            "device missing",
        )

    def test_reports_close_error(self) -> None:
        car = Mock()
        car.close.side_effect = HardwareError("close failed")

        with patch(
            "betabox_robotics.BetaboxCar",
            return_value=car,
        ):
            result = check_robot_constructs()

        self.assertEqual(
            result,
            CheckResult(
                name="robot:construct",
                ok=False,
                message=("BetaboxCar constructed but could not close: close failed"),
            ),
        )

    def test_unexpected_construction_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                "betabox_robotics.BetaboxCar",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_robot_constructs()

        self.assertIs(
            context.exception,
            error,
        )

    def test_unexpected_close_error_propagates(
        self,
    ) -> None:
        car = Mock()
        error = RuntimeError("programming error")
        car.close.side_effect = error

        with (
            patch(
                "betabox_robotics.BetaboxCar",
                return_value=car,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_robot_constructs()

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_robot_config_before_constructing(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.BetaboxCar") as betabox_car,
            self.assertRaisesRegex(
                TypeError,
                ("robot_config must be a RobotConfig"),
            ),
        ):
            check_robot_constructs(
                robot_config=object(),  # type: ignore[arg-type]
            )

        betabox_car.assert_not_called()


class ChecksFromHardwareStatusTests(unittest.TestCase):
    def test_returns_complete_healthy_checks(
        self,
    ) -> None:
        hardware = make_hardware_status()

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result,
            (
                CheckResult(
                    name="hardware:i2c",
                    ok=True,
                    message="0x14",
                ),
                CheckResult(
                    name="hardware:robot",
                    ok=True,
                    message=("robot hardware available"),
                ),
                CheckResult(
                    name="hardware:battery",
                    ok=True,
                    message="8.20 V — ok",
                ),
                CheckResult(
                    name="hardware:grayscale",
                    ok=True,
                    message=("100.0, 200.0, 300.0"),
                ),
                CheckResult(
                    name=("hardware:ultrasonic_configured"),
                    ok=True,
                    message=("ultrasonic configured"),
                ),
                CheckResult(
                    name="audio:hifiberry",
                    ok=True,
                    message="HifiBerry DAC",
                ),
                CheckResult(
                    name="vision:service",
                    ok=True,
                    message=("Vision service and camera pipeline healthy"),
                ),
            ),
        )

    def test_i2c_uses_error_without_devices(
        self,
    ) -> None:
        hardware = make_hardware_status(
            i2c_available=False,
            i2c_devices=[],
            i2c_error="I2C unavailable",
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[0],
            CheckResult(
                name="hardware:i2c",
                ok=False,
                message="I2C unavailable",
            ),
        )

    def test_i2c_uses_default_without_error(
        self,
    ) -> None:
        hardware = make_hardware_status(
            i2c_available=False,
            i2c_devices=[],
            i2c_error=None,
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[0].message,
            "no I2C devices detected",
        )

    def test_passive_hardware_uses_error(
        self,
    ) -> None:
        hardware = make_hardware_status(
            passive_available=False,
            passive_error="robot unavailable",
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[1],
            CheckResult(
                name="hardware:robot",
                ok=False,
                message="robot unavailable",
            ),
        )

    def test_low_battery_is_still_ok(self) -> None:
        hardware = make_hardware_status(
            battery_state="low",
            battery_voltage=7.0,
        )

        result = checks_from_hardware_status(hardware)

        self.assertTrue(result[2].ok)
        self.assertEqual(
            result[2].message,
            "7.00 V — low",
        )

    def test_critical_battery_fails(self) -> None:
        hardware = make_hardware_status(
            battery_state="critical",
            battery_voltage=6.0,
        )

        result = checks_from_hardware_status(hardware)

        self.assertFalse(result[2].ok)
        self.assertEqual(
            result[2].message,
            "6.00 V — critical",
        )

    def test_unavailable_battery_uses_error(
        self,
    ) -> None:
        hardware = make_hardware_status(
            battery_available=False,
            battery_voltage=None,
            battery_state="unknown",
            battery_error="ADC unavailable",
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[2],
            CheckResult(
                name="hardware:battery",
                ok=False,
                message="ADC unavailable",
            ),
        )

    def test_unavailable_battery_uses_default_message(
        self,
    ) -> None:
        hardware = make_hardware_status(
            battery_available=False,
            battery_voltage=None,
            battery_state="unknown",
            battery_error=None,
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[2].message,
            "battery unavailable",
        )

    def test_grayscale_uses_values(self) -> None:
        hardware = make_hardware_status(
            grayscale_values=[
                1.0,
                2.5,
                3.0,
            ],
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[3].message,
            "1.0, 2.5, 3.0",
        )

    def test_unavailable_grayscale_uses_error(
        self,
    ) -> None:
        hardware = make_hardware_status(
            grayscale_available=False,
            sensor_error="sensor failed",
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[3],
            CheckResult(
                name="hardware:grayscale",
                ok=False,
                message="sensor failed",
            ),
        )

    def test_unconfigured_ultrasonic_fails(
        self,
    ) -> None:
        hardware = make_hardware_status(
            ultrasonic_configured=False,
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[4],
            CheckResult(
                name=("hardware:ultrasonic_configured"),
                ok=False,
                message=("ultrasonic not configured"),
            ),
        )

    def test_unavailable_audio_uses_error(
        self,
    ) -> None:
        hardware = make_hardware_status(
            audio_available=False,
            audio_device=None,
            audio_error="audio failed",
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[5],
            CheckResult(
                name="audio:hifiberry",
                ok=False,
                message="audio failed",
            ),
        )

    def test_unavailable_audio_uses_default(
        self,
    ) -> None:
        hardware = make_hardware_status(
            audio_available=False,
            audio_device=None,
            audio_error=None,
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[5].message,
            "audio unavailable",
        )

    def test_degraded_vision_uses_error(
        self,
    ) -> None:
        hardware = make_hardware_status(
            vision_camera_has_frame=False,
            vision_error="no camera frame",
        )

        result = checks_from_hardware_status(hardware)

        self.assertEqual(
            result[6],
            CheckResult(
                name="vision:service",
                ok=False,
                message="no camera frame",
            ),
        )

    def test_degraded_vision_uses_default(
        self,
    ) -> None:
        hardware = make_hardware_status(
            vision_running=False,
            vision_error=None,
        )

        result = checks_from_hardware_status(hardware)

        self.assertFalse(result[6].ok)
        self.assertEqual(
            result[6].message,
            "Vision service degraded",
        )

    def test_rejects_invalid_hardware_before_access(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("hardware must be a RobotHardwareStatus"),
        ):
            checks_from_hardware_status(
                object()  # type: ignore[arg-type]
            )


class CheckUltrasonicReadTests(unittest.TestCase):
    def test_reports_distance(self) -> None:
        sensors = Mock()
        sensors.ultrasonic.distance.return_value = 42.25

        with patch(
            "betabox_robotics.sensors.Sensors.default",
            return_value=sensors,
        ) as sensors_default:
            result = check_ultrasonic_read()

        sensors_default.assert_called_once_with(BETABOX_CAR.sensors)
        sensors.ultrasonic.distance.assert_called_once_with(samples=3)
        sensors.close.assert_called_once_with()
        self.assertEqual(
            result,
            CheckResult(
                name="hardware:ultrasonic_read",
                ok=True,
                message="42.2 cm",
            ),
        )

    def test_converts_string_distance(self) -> None:
        sensors = Mock()
        sensors.ultrasonic.distance.return_value = "12.5"

        with patch(
            "betabox_robotics.sensors.Sensors.default",
            return_value=sensors,
        ):
            result = check_ultrasonic_read()

        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            "12.5 cm",
        )

    def test_reports_negative_distance(self) -> None:
        sensors = Mock()
        sensors.ultrasonic.distance.return_value = -1

        with patch(
            "betabox_robotics.sensors.Sensors.default",
            return_value=sensors,
        ):
            result = check_ultrasonic_read()

        sensors.close.assert_called_once_with()
        self.assertEqual(
            result,
            CheckResult(
                name="hardware:ultrasonic_read",
                ok=False,
                message=("invalid distance result: -1.0"),
            ),
        )

    def test_reports_sensor_construction_error(
        self,
    ) -> None:
        with patch(
            "betabox_robotics.sensors.Sensors.default",
            side_effect=SensorError("sensor unavailable"),
        ):
            result = check_ultrasonic_read()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:ultrasonic_read",
                ok=False,
                message="sensor unavailable",
            ),
        )

    def test_reports_distance_error(self) -> None:
        sensors = Mock()
        sensors.ultrasonic.distance.side_effect = HardwareError("read failed")

        with patch(
            "betabox_robotics.sensors.Sensors.default",
            return_value=sensors,
        ):
            result = check_ultrasonic_read()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:ultrasonic_read",
                ok=False,
                message="read failed",
            ),
        )

    def test_reports_invalid_distance_value(
        self,
    ) -> None:
        sensors = Mock()
        sensors.ultrasonic.distance.return_value = "invalid"

        with patch(
            "betabox_robotics.sensors.Sensors.default",
            return_value=sensors,
        ):
            result = check_ultrasonic_read()

        self.assertFalse(result.ok)
        self.assertIn(
            "could not convert string to float",
            result.message,
        )

    def test_reports_cleanup_failure(self) -> None:
        sensors = Mock()
        sensors.ultrasonic.distance.return_value = 42.0
        sensors.close.side_effect = SensorError("close failed")

        with patch(
            "betabox_robotics.sensors.Sensors.default",
            return_value=sensors,
        ):
            result = check_ultrasonic_read()

        self.assertEqual(
            result,
            CheckResult(
                name="hardware:ultrasonic_read",
                ok=False,
                message=("ultrasonic read succeeded but cleanup failed: close failed"),
            ),
        )

    def test_allows_missing_close_method(
        self,
    ) -> None:
        ultrasonic = Mock()
        ultrasonic.distance.return_value = 25.0
        sensors = Mock(
            spec=[
                "ultrasonic",
            ]
        )
        sensors.ultrasonic = ultrasonic

        with patch(
            "betabox_robotics.sensors.Sensors.default",
            return_value=sensors,
        ):
            result = check_ultrasonic_read()

        self.assertTrue(result.ok)

    def test_unexpected_sensor_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                "betabox_robotics.sensors.Sensors.default",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_ultrasonic_read()

        self.assertIs(
            context.exception,
            error,
        )

    def test_unexpected_close_error_propagates(
        self,
    ) -> None:
        sensors = Mock()
        sensors.ultrasonic.distance.return_value = 42.0
        error = RuntimeError("programming error")
        sensors.close.side_effect = error

        with (
            patch(
                "betabox_robotics.sensors.Sensors.default",
                return_value=sensors,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            check_ultrasonic_read()

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_robot_config_before_sensors(
        self,
    ) -> None:
        with (
            patch("betabox_robotics.sensors.Sensors.default") as sensors_default,
            self.assertRaisesRegex(
                TypeError,
                ("robot_config must be a RobotConfig"),
            ),
        ):
            check_ultrasonic_read(
                robot_config=object(),  # type: ignore[arg-type]
            )

        sensors_default.assert_not_called()


DEFAULT_VERIFICATION = __import__(
    "betabox_robotics.config",
    fromlist=["DEFAULT_PLATFORM_CONFIG"],
).DEFAULT_PLATFORM_CONFIG.verification

DEFAULT_I2C_PATH = DEFAULT_VERIFICATION.i2c_device


if __name__ == "__main__":
    unittest.main()
