from __future__ import annotations

import unittest
from unittest.mock import Mock, call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.robots.betabox_car import (
    BETABOX_CAR,
)
from betabox_robotics.services.hardware_checks import (
    RobotHardwareStatus,
)
from betabox_robotics.services.verify_checks.collection import (
    _validate_robot_config,
    collect_checks,
)
from betabox_robotics.services.verify_checks.models import (
    CheckResult,
)

MODULE = "betabox_robotics.services.verify_checks.collection"


def make_check(
    name: str,
    *,
    ok: bool = True,
    message: str = "",
) -> CheckResult:
    return CheckResult(
        name=name,
        ok=ok,
        message=message,
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


class CollectChecksTests(unittest.TestCase):
    def test_collects_all_checks_in_order(
        self,
    ) -> None:
        config = DEFAULT_PLATFORM_CONFIG
        verification = config.verification

        import_results = tuple(
            make_check(
                f"import:{module}",
                message="import ok",
            )
            for module in (verification.required_python_modules)
        )

        picamera_result = make_check(
            "camera:picamera2",
            message="import ok",
        )
        proxy_result = make_check(
            "jupyterhub:proxy",
            message="5.0.0",
        )
        launchpad_result = make_check(
            "launchpad:http",
            message="Launchpad responding",
        )
        speech_result = make_check(
            "audio:speech_backend",
            message="espeak-ng",
        )

        media_results = (
            make_check(
                "media:pictures",
                message="/media/pictures",
            ),
            make_check(
                "media:videos",
                message="/media/videos",
            ),
            make_check(
                "media:sounds",
                message="/media/sounds",
            ),
        )

        hardware = Mock(spec=RobotHardwareStatus)

        hardware_results = (
            make_check(
                "hardware:i2c",
                message="0x14",
            ),
            make_check(
                "hardware:robot",
                message="robot hardware available",
            ),
            make_check(
                "hardware:battery",
                message="8.20 V — ok",
            ),
        )

        robot_result = make_check(
            "robot:construct",
            message=("BetaboxCar constructed successfully"),
        )

        with (
            patch(
                f"{MODULE}.check_import",
                side_effect=import_results,
            ) as check_import,
            patch(
                f"{MODULE}.check_picamera2",
                return_value=picamera_result,
            ) as check_picamera2,
            patch(
                (f"{MODULE}.check_configurable_http_proxy"),
                return_value=proxy_result,
            ) as check_proxy,
            patch(
                f"{MODULE}.check_launchpad",
                return_value=launchpad_result,
            ) as check_launchpad,
            patch(
                f"{MODULE}.check_speech_backend",
                return_value=speech_result,
            ) as check_speech,
            patch(
                f"{MODULE}.check_media_paths",
                return_value=media_results,
            ) as check_media,
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=hardware,
            ) as collect_hardware,
            patch(
                (f"{MODULE}.checks_from_hardware_status"),
                return_value=hardware_results,
            ) as convert_hardware,
            patch(
                f"{MODULE}.check_robot_constructs",
                return_value=robot_result,
            ) as check_robot,
        ):
            result = collect_checks(
                include_robot=True,
                config=config,
                robot_config=BETABOX_CAR,
            )

        expected = (
            *import_results,
            picamera_result,
            proxy_result,
            launchpad_result,
            speech_result,
            *media_results,
            *hardware_results,
            robot_result,
        )

        self.assertEqual(
            result,
            expected,
        )
        self.assertIsInstance(
            result,
            tuple,
        )

        self.assertEqual(
            check_import.call_args_list,
            [call(module) for module in (verification.required_python_modules)],
        )
        check_picamera2.assert_called_once_with()
        check_proxy.assert_called_once_with(
            timeout=(verification.command_timeout_seconds)
        )
        check_launchpad.assert_called_once_with(config)
        check_speech.assert_called_once_with()
        check_media.assert_called_once_with(config)
        collect_hardware.assert_called_once_with(
            config,
            robot_config=BETABOX_CAR,
        )
        convert_hardware.assert_called_once_with(hardware)
        check_robot.assert_called_once_with(
            robot_config=BETABOX_CAR,
        )

    def test_excludes_robot_construction_check(
        self,
    ) -> None:
        hardware = Mock(spec=RobotHardwareStatus)
        hardware_results = (make_check("hardware:i2c"),)

        with (
            patch(
                f"{MODULE}.check_import",
                return_value=make_check("import:test"),
            ),
            patch(
                f"{MODULE}.check_picamera2",
                return_value=make_check("camera:picamera2"),
            ),
            patch(
                (f"{MODULE}.check_configurable_http_proxy"),
                return_value=make_check("jupyterhub:proxy"),
            ),
            patch(
                f"{MODULE}.check_launchpad",
                return_value=make_check("launchpad:http"),
            ),
            patch(
                f"{MODULE}.check_speech_backend",
                return_value=make_check("audio:speech_backend"),
            ),
            patch(
                f"{MODULE}.check_media_paths",
                return_value=(),
            ),
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=hardware,
            ),
            patch(
                (f"{MODULE}.checks_from_hardware_status"),
                return_value=hardware_results,
            ),
            patch(f"{MODULE}.check_robot_constructs") as check_robot,
        ):
            result = collect_checks(include_robot=False)

        check_robot.assert_not_called()
        self.assertEqual(
            result[-1],
            hardware_results[-1],
        )
        self.assertNotIn(
            "robot:construct",
            tuple(check.name for check in result),
        )

    def test_uses_default_values(self) -> None:
        hardware = Mock(spec=RobotHardwareStatus)

        with (
            patch(
                f"{MODULE}.check_import",
                return_value=make_check("import:test"),
            ),
            patch(
                f"{MODULE}.check_picamera2",
                return_value=make_check("camera:picamera2"),
            ),
            patch(
                (f"{MODULE}.check_configurable_http_proxy"),
                return_value=make_check("jupyterhub:proxy"),
            ),
            patch(
                f"{MODULE}.check_launchpad",
                return_value=make_check("launchpad:http"),
            ) as check_launchpad,
            patch(
                f"{MODULE}.check_speech_backend",
                return_value=make_check("audio:speech_backend"),
            ),
            patch(
                f"{MODULE}.check_media_paths",
                return_value=(),
            ) as check_media,
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=hardware,
            ) as collect_hardware,
            patch(
                (f"{MODULE}.checks_from_hardware_status"),
                return_value=(),
            ),
            patch(
                f"{MODULE}.check_robot_constructs",
                return_value=make_check("robot:construct"),
            ) as check_robot,
        ):
            collect_checks()

        check_launchpad.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        check_media.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_hardware.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG,
            robot_config=BETABOX_CAR,
        )
        check_robot.assert_called_once_with(
            robot_config=BETABOX_CAR,
        )

    def test_preserves_failed_results(self) -> None:
        failed_import = make_check(
            "import:missing",
            ok=False,
            message="module missing",
        )
        failed_launchpad = make_check(
            "launchpad:http",
            ok=False,
            message="service inactive",
        )
        hardware = Mock(spec=RobotHardwareStatus)
        failed_hardware = make_check(
            "hardware:battery",
            ok=False,
            message="battery unavailable",
        )

        with (
            patch(
                f"{MODULE}.check_import",
                return_value=failed_import,
            ),
            patch(
                f"{MODULE}.check_picamera2",
                return_value=make_check("camera:picamera2"),
            ),
            patch(
                (f"{MODULE}.check_configurable_http_proxy"),
                return_value=make_check("jupyterhub:proxy"),
            ),
            patch(
                f"{MODULE}.check_launchpad",
                return_value=failed_launchpad,
            ),
            patch(
                f"{MODULE}.check_speech_backend",
                return_value=make_check("audio:speech_backend"),
            ),
            patch(
                f"{MODULE}.check_media_paths",
                return_value=(),
            ),
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=hardware,
            ),
            patch(
                (f"{MODULE}.checks_from_hardware_status"),
                return_value=(failed_hardware,),
            ),
            patch(
                f"{MODULE}.check_robot_constructs",
                return_value=make_check("robot:construct"),
            ),
        ):
            result = collect_checks()

        self.assertIn(
            failed_import,
            result,
        )
        self.assertIn(
            failed_launchpad,
            result,
        )
        self.assertIn(
            failed_hardware,
            result,
        )

    def test_rejects_invalid_config_before_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_import") as check_import,
            patch(f"{MODULE}.collect_hardware_status") as collect_hardware,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_checks(
                config=object(),  # type: ignore[arg-type]
            )

        check_import.assert_not_called()
        collect_hardware.assert_not_called()

    def test_rejects_invalid_include_robot_before_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_import") as check_import,
            patch(f"{MODULE}.collect_hardware_status") as collect_hardware,
            self.assertRaisesRegex(
                TypeError,
                ("include_robot must be a boolean"),
            ),
        ):
            collect_checks(
                include_robot=1,  # type: ignore[arg-type]
            )

        check_import.assert_not_called()
        collect_hardware.assert_not_called()

    def test_rejects_invalid_robot_config_before_checks(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.check_import") as check_import,
            patch(f"{MODULE}.collect_hardware_status") as collect_hardware,
            self.assertRaisesRegex(
                TypeError,
                ("robot_config must be a RobotConfig"),
            ),
        ):
            collect_checks(
                robot_config=object(),  # type: ignore[arg-type]
            )

        check_import.assert_not_called()
        collect_hardware.assert_not_called()

    def test_import_check_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("import check failed")

        with (
            patch(
                f"{MODULE}.check_import",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_checks()

        self.assertIs(
            context.exception,
            error,
        )

    def test_hardware_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("hardware collection failed")

        with (
            patch(
                f"{MODULE}.check_import",
                return_value=make_check("import:test"),
            ),
            patch(
                f"{MODULE}.check_picamera2",
                return_value=make_check("camera:picamera2"),
            ),
            patch(
                (f"{MODULE}.check_configurable_http_proxy"),
                return_value=make_check("jupyterhub:proxy"),
            ),
            patch(
                f"{MODULE}.check_launchpad",
                return_value=make_check("launchpad:http"),
            ),
            patch(
                f"{MODULE}.check_speech_backend",
                return_value=make_check("audio:speech_backend"),
            ),
            patch(
                f"{MODULE}.check_media_paths",
                return_value=(),
            ),
            patch(
                f"{MODULE}.collect_hardware_status",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_checks()

        self.assertIs(
            context.exception,
            error,
        )

    def test_robot_check_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("robot check failed")
        hardware = Mock(spec=RobotHardwareStatus)

        with (
            patch(
                f"{MODULE}.check_import",
                return_value=make_check("import:test"),
            ),
            patch(
                f"{MODULE}.check_picamera2",
                return_value=make_check("camera:picamera2"),
            ),
            patch(
                (f"{MODULE}.check_configurable_http_proxy"),
                return_value=make_check("jupyterhub:proxy"),
            ),
            patch(
                f"{MODULE}.check_launchpad",
                return_value=make_check("launchpad:http"),
            ),
            patch(
                f"{MODULE}.check_speech_backend",
                return_value=make_check("audio:speech_backend"),
            ),
            patch(
                f"{MODULE}.check_media_paths",
                return_value=(),
            ),
            patch(
                f"{MODULE}.collect_hardware_status",
                return_value=hardware,
            ),
            patch(
                (f"{MODULE}.checks_from_hardware_status"),
                return_value=(),
            ),
            patch(
                f"{MODULE}.check_robot_constructs",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_checks()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
