from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.video import (
    _validate_fps,
    _validate_port,
    _validate_string,
    log,
    main,
    run_video_service,
)

MODULE = "betabox_robotics.services.video"


class ValidateStringTests(unittest.TestCase):
    def test_accepts_and_normalizes_string(self) -> None:
        self.assertEqual(
            _validate_string(
                " 0.0.0.0 ",
                name="host",
            ),
            "0.0.0.0",
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "host must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="host",
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
                    "host cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="host",
                )


class ValidatePortTests(unittest.TestCase):
    def test_accepts_port_boundaries(self) -> None:
        for value in (
            1,
            65535,
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    _validate_port(value),
                    value,
                )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            False,
            8080.0,
            "8080",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "port must be an integer",
                ),
            ):
                _validate_port(value)

    def test_rejects_port_outside_range(self) -> None:
        for value in (
            0,
            -1,
            65536,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "port must be between 1 and 65535",
                ),
            ):
                _validate_port(value)


class ValidateFpsTests(unittest.TestCase):
    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_fps(20),
            20,
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            False,
            20.0,
            "20",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "fps must be an integer",
                ),
            ):
                _validate_fps(value)

    def test_rejects_non_positive_value(self) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "fps must be greater than 0",
                ),
            ):
                _validate_fps(value)


class LogTests(unittest.TestCase):
    def test_writes_timestamped_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_dir = root / "state"
            video_log = state_dir / "video.log"

            config = MagicMock(spec=type(DEFAULT_PLATFORM_CONFIG))
            config.paths.state_dir = state_dir
            config.paths.video_log = video_log

            # The function requires a real PlatformConfig instance.
            # Patch isinstance inside this module for this isolated
            # filesystem test.
            with (
                patch(
                    f"{MODULE}.PlatformConfig",
                    type(DEFAULT_PLATFORM_CONFIG),
                ),
                patch(
                    f"{MODULE}.time.strftime",
                    return_value="2026-08-05 12:30:00",
                ),
            ):
                log(
                    " service started ",
                    config,  # type: ignore[arg-type]
                )

            self.assertTrue(state_dir.is_dir())
            self.assertEqual(
                video_log.read_text(encoding="utf-8"),
                ("2026-08-05 12:30:00 service started\n"),
            )

    def test_appends_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_dir = root / "state"
            video_log = state_dir / "video.log"

            config = MagicMock(spec=type(DEFAULT_PLATFORM_CONFIG))
            config.paths.state_dir = state_dir
            config.paths.video_log = video_log

            with (
                patch(
                    f"{MODULE}.PlatformConfig",
                    type(DEFAULT_PLATFORM_CONFIG),
                ),
                patch(
                    f"{MODULE}.time.strftime",
                    side_effect=(
                        "2026-08-05 12:30:00",
                        "2026-08-05 12:30:01",
                    ),
                ),
            ):
                log(
                    "first",
                    config,  # type: ignore[arg-type]
                )
                log(
                    "second",
                    config,  # type: ignore[arg-type]
                )

            self.assertEqual(
                video_log.read_text(encoding="utf-8"),
                ("2026-08-05 12:30:00 first\n2026-08-05 12:30:01 second\n"),
            )

    def test_rejects_invalid_config(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "config must be a PlatformConfig",
        ):
            log(
                "message",
                object(),  # type: ignore[arg-type]
            )

    def test_rejects_invalid_message_before_filesystem_access(
        self,
    ) -> None:
        config = MagicMock(spec=type(DEFAULT_PLATFORM_CONFIG))

        with self.assertRaisesRegex(
            ValueError,
            "message cannot be empty",
        ):
            log(
                " ",
                config,  # type: ignore[arg-type]
            )

        config.paths.state_dir.mkdir.assert_not_called()

    def test_ignores_directory_creation_failure(self) -> None:
        with patch.object(
            DEFAULT_PLATFORM_CONFIG.paths.state_dir.__class__,
            "mkdir",
            side_effect=OSError("permission denied"),
        ):
            self.assertIsNone(
                log(
                    "message",
                    DEFAULT_PLATFORM_CONFIG,
                )
            )

    def test_ignores_log_open_failure(self) -> None:
        with (
            patch.object(
                DEFAULT_PLATFORM_CONFIG.paths.state_dir.__class__,
                "mkdir",
            ),
            patch.object(
                DEFAULT_PLATFORM_CONFIG.paths.video_log.__class__,
                "open",
                side_effect=OSError("permission denied"),
            ),
        ):
            self.assertIsNone(
                log(
                    "message",
                    DEFAULT_PLATFORM_CONFIG,
                )
            )


class RunVideoServiceTests(unittest.TestCase):
    def test_uses_default_configuration(self) -> None:
        service = MagicMock()

        with (
            patch(f"{MODULE}.VisionServiceConfig") as config_type,
            patch(
                f"{MODULE}.VisionService",
                return_value=service,
            ) as service_type,
            patch(f"{MODULE}.log") as log_message,
        ):
            result = run_video_service()

        self.assertEqual(
            result,
            0,
        )
        config_type.assert_called_once_with(
            host=(DEFAULT_PLATFORM_CONFIG.network.bind_host),
            port=(DEFAULT_PLATFORM_CONFIG.network.vision_port),
            fps=(DEFAULT_PLATFORM_CONFIG.runtime.vision_fps),
        )
        service_type.assert_called_once_with(config_type.return_value)
        service.run.assert_called_once_with()
        service.stop.assert_called_once_with()

        self.assertEqual(
            log_message.call_args_list,
            [
                call(
                    (
                        "starting video service "
                        f"host={DEFAULT_PLATFORM_CONFIG.network.bind_host} "
                        f"port={DEFAULT_PLATFORM_CONFIG.network.vision_port} "
                        f"fps={DEFAULT_PLATFORM_CONFIG.runtime.vision_fps}"
                    ),
                    DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    "stopping video service",
                    DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    "video service stopped",
                    DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )

    def test_uses_overrides(self) -> None:
        service = MagicMock()

        with (
            patch(f"{MODULE}.VisionServiceConfig") as config_type,
            patch(
                f"{MODULE}.VisionService",
                return_value=service,
            ),
            patch(f"{MODULE}.log"),
        ):
            result = run_video_service(
                host=" 127.0.0.1 ",
                port=9000,
                fps=30,
            )

        self.assertEqual(
            result,
            0,
        )
        config_type.assert_called_once_with(
            host="127.0.0.1",
            port=9000,
            fps=30,
        )

    def test_rejects_invalid_config_before_service_creation(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.VisionService") as service_type,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            run_video_service(
                config=object(),  # type: ignore[arg-type]
            )

        service_type.assert_not_called()

    def test_rejects_invalid_values_before_service_creation(
        self,
    ) -> None:
        cases = (
            (
                {
                    "host": " ",
                },
                ValueError,
                "host cannot be empty",
            ),
            (
                {
                    "port": True,
                },
                TypeError,
                "port must be an integer",
            ),
            (
                {
                    "port": 0,
                },
                ValueError,
                "port must be between",
            ),
            (
                {
                    "fps": True,
                },
                TypeError,
                "fps must be an integer",
            ),
            (
                {
                    "fps": 0,
                },
                ValueError,
                "fps must be greater than",
            ),
        )

        for kwargs, error_type, message in cases:
            with (
                self.subTest(kwargs=kwargs),
                patch(f"{MODULE}.VisionService") as service_type,
                self.assertRaisesRegex(
                    error_type,
                    message,
                ),
            ):
                run_video_service(
                    **kwargs  # type: ignore[arg-type]
                )

            service_type.assert_not_called()

    def test_keyboard_interrupt_is_handled(self) -> None:
        service = MagicMock()
        service.run.side_effect = KeyboardInterrupt

        with (
            patch(
                f"{MODULE}.VisionService",
                return_value=service,
            ),
            patch(f"{MODULE}.log") as log_message,
        ):
            result = run_video_service()

        self.assertEqual(
            result,
            0,
        )
        service.stop.assert_called_once_with()
        self.assertIn(
            call(
                "video service interrupted",
                DEFAULT_PLATFORM_CONFIG,
            ),
            log_message.call_args_list,
        )
        self.assertIn(
            call(
                "video service stopped",
                DEFAULT_PLATFORM_CONFIG,
            ),
            log_message.call_args_list,
        )

    def test_runtime_error_is_logged_and_propagated(
        self,
    ) -> None:
        service = MagicMock()
        runtime_error = RuntimeError("camera failed")
        service.run.side_effect = runtime_error

        with (
            patch(
                f"{MODULE}.VisionService",
                return_value=service,
            ),
            patch(f"{MODULE}.log") as log_message,
            self.assertRaises(RuntimeError) as context,
        ):
            run_video_service()

        self.assertIs(
            context.exception,
            runtime_error,
        )
        service.stop.assert_called_once_with()
        self.assertIn(
            call(
                "video service failed: camera failed",
                DEFAULT_PLATFORM_CONFIG,
            ),
            log_message.call_args_list,
        )

    def test_stop_failure_is_logged_and_suppressed(
        self,
    ) -> None:
        service = MagicMock()
        service.stop.side_effect = RuntimeError("stop failed")

        with (
            patch(
                f"{MODULE}.VisionService",
                return_value=service,
            ),
            patch(f"{MODULE}.log") as log_message,
            patch(f"{MODULE}.logger.exception") as logger_exception,
        ):
            result = run_video_service()

        self.assertEqual(
            result,
            0,
        )
        logger_exception.assert_called_once_with(
            "Video service failed to stop cleanly."
        )
        self.assertIn(
            call(
                "video service stop failed",
                DEFAULT_PLATFORM_CONFIG,
            ),
            log_message.call_args_list,
        )
        self.assertNotIn(
            call(
                "video service stopped",
                DEFAULT_PLATFORM_CONFIG,
            ),
            log_message.call_args_list,
        )

    def test_stop_failure_does_not_mask_run_failure(
        self,
    ) -> None:
        service = MagicMock()
        run_error = RuntimeError("run failed")
        service.run.side_effect = run_error
        service.stop.side_effect = RuntimeError("stop failed")

        with (
            patch(
                f"{MODULE}.VisionService",
                return_value=service,
            ),
            patch(f"{MODULE}.log"),
            patch(f"{MODULE}.logger.exception"),
            self.assertRaises(RuntimeError) as context,
        ):
            run_video_service()

        self.assertIs(
            context.exception,
            run_error,
        )


class MainTests(unittest.TestCase):
    def test_forwards_arguments(self) -> None:
        with patch(
            f"{MODULE}.run_video_service",
            return_value=0,
        ) as run:
            result = main(
                [
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "9000",
                    "--fps",
                    "30",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        run.assert_called_once_with(
            host="127.0.0.1",
            port=9000,
            fps=30,
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_uses_defaults(self) -> None:
        with patch(
            f"{MODULE}.run_video_service",
            return_value=0,
        ) as run:
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        run.assert_called_once_with(
            host=(DEFAULT_PLATFORM_CONFIG.network.bind_host),
            port=(DEFAULT_PLATFORM_CONFIG.network.vision_port),
            fps=(DEFAULT_PLATFORM_CONFIG.runtime.vision_fps),
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_returns_one_for_validation_error(self) -> None:
        with (
            patch(
                f"{MODULE}.run_video_service",
                side_effect=ValueError("invalid video settings"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once()

        printed = print_message.call_args.args[0]

        self.assertIsInstance(
            printed,
            ValueError,
        )
        self.assertEqual(
            str(printed),
            "invalid video settings",
        )

    def test_returns_one_for_type_error(self) -> None:
        with (
            patch(
                f"{MODULE}.run_video_service",
                side_effect=TypeError("invalid type"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once()

        printed = print_message.call_args.args[0]

        self.assertIsInstance(
            printed,
            TypeError,
        )
        self.assertEqual(
            str(printed),
            "invalid type",
        )

    def test_unexpected_error_propagates(self) -> None:
        error = RuntimeError("service failed")

        with (
            patch(
                f"{MODULE}.run_video_service",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
