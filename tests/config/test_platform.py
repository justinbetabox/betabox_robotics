from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    LaunchpadConfig,
    PlatformConfig,
    PlatformHealthConfig,
    PlatformMonitoringConfig,
    PlatformNetworkConfig,
    PlatformPathsConfig,
    PlatformRuntimeConfig,
    PlatformServicesConfig,
    PlatformVerificationConfig,
    ServiceCategory,
    ServiceDefinition,
    ServiceStartup,
    TemperatureThresholdConfig,
    UsageThresholdConfig,
)


class PlatformPathsConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = PlatformPathsConfig(
            home=Path("/home/picar"),
            repository_root=Path("/opt/libs/betabox_robotics"),
        )

    def test_default(self) -> None:
        with patch(
            "betabox_robotics.config.platform.Path.home",
            return_value=Path("/home/picar"),
        ):
            config = PlatformPathsConfig.default()

        self.assertEqual(
            config.home,
            Path("/home/picar"),
        )
        self.assertEqual(
            config.repository_root,
            Path("/opt/libs/betabox_robotics"),
        )

    def test_rejects_invalid_home_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "home must be a Path",
        ):
            PlatformPathsConfig(
                home="/home/picar",  # type: ignore[arg-type]
                repository_root=Path("/opt/libs/betabox_robotics"),
            )

    def test_rejects_invalid_repository_root_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "repository_root must be a Path",
        ):
            PlatformPathsConfig(
                home=Path("/home/picar"),
                repository_root="/opt/libs",  # type: ignore[arg-type]
            )

    def test_media_paths(self) -> None:
        self.assertEqual(
            self.config.media_root,
            Path("/home/picar/media"),
        )
        self.assertEqual(
            self.config.pictures_dir,
            Path("/home/picar/media/pictures"),
        )
        self.assertEqual(
            self.config.videos_dir,
            Path("/home/picar/media/videos"),
        )
        self.assertEqual(
            self.config.sounds_dir,
            Path("/home/picar/media/sounds"),
        )

    def test_state_paths(self) -> None:
        state_dir = Path("/home/picar/.local/state/betabox")

        self.assertEqual(
            self.config.state_dir,
            state_dir,
        )
        self.assertEqual(
            self.config.calibration_file,
            state_dir / "calibration.json",
        )
        self.assertEqual(
            self.config.events_file,
            state_dir / "events.jsonl",
        )
        self.assertEqual(
            self.config.monitor_log,
            state_dir / "monitor.log",
        )
        self.assertEqual(
            self.config.boot_announce_log,
            state_dir / "boot_announce.log",
        )
        self.assertEqual(
            self.config.video_log,
            state_dir / "video.log",
        )

    def test_backup_and_snapshot_roots(self) -> None:
        self.assertEqual(
            self.config.backup_root,
            Path("/home/picar/betabox-backups"),
        )
        self.assertEqual(
            self.config.snapshot_root,
            Path("/home/picar/betabox-snapshots"),
        )

    def test_repository_paths(self) -> None:
        self.assertEqual(
            self.config.docs_dir,
            Path("/opt/libs/betabox_robotics/docs"),
        )
        self.assertEqual(
            self.config.deployment_dir,
            Path("/opt/libs/betabox_robotics/deployment"),
        )

    def test_backup_sources(self) -> None:
        self.assertEqual(
            self.config.backup_sources,
            (
                self.config.media_root,
                self.config.config_dir,
                self.config.state_dir,
                self.config.docs_dir,
                self.config.deployment_dir,
            ),
        )

    def test_restore_paths(self) -> None:
        self.assertEqual(
            self.config.restore_paths,
            (
                self.config.media_root,
                self.config.config_dir,
                self.config.state_dir,
            ),
        )

    def test_reset_paths(self) -> None:
        self.assertEqual(
            self.config.reset_paths,
            (
                self.config.pictures_dir,
                self.config.videos_dir,
            ),
        )

    def test_recreate_paths(self) -> None:
        self.assertEqual(
            self.config.recreate_paths,
            (
                self.config.pictures_dir,
                self.config.videos_dir,
                self.config.sounds_dir,
            ),
        )

    def test_car_honk_sound(self) -> None:
        self.assertEqual(
            self.config.car_honk_sound,
            Path("/home/picar/media/sounds/car-honk.mp3"),
        )


class UsageThresholdConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = UsageThresholdConfig()

        self.assertEqual(
            config.high_percent,
            85.0,
        )
        self.assertEqual(
            config.critical_percent,
            95.0,
        )

    def test_normalizes_integer_values_to_float(
        self,
    ) -> None:
        config = UsageThresholdConfig(
            high_percent=80,
            critical_percent=90,
        )

        self.assertEqual(
            config.high_percent,
            80.0,
        )
        self.assertEqual(
            config.critical_percent,
            90.0,
        )
        self.assertIsInstance(
            config.high_percent,
            float,
        )

    def test_rejects_non_numeric_values(self) -> None:
        for field_name in (
            "high_percent",
            "critical_percent",
        ):
            for value in (
                True,
                "85",
                object(),
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(TypeError),
                ):
                    values = {
                        "high_percent": 85.0,
                        "critical_percent": 95.0,
                    }
                    values[field_name] = value

                    UsageThresholdConfig(
                        **values  # type: ignore[arg-type]
                    )

    def test_rejects_non_finite_values(self) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(ValueError),
            ):
                UsageThresholdConfig(
                    high_percent=value,
                )

    def test_rejects_percentages_outside_range(
        self,
    ) -> None:
        for field_name, value in (
            ("high_percent", -0.1),
            ("high_percent", 100.1),
            ("critical_percent", -0.1),
            ("critical_percent", 100.1),
        ):
            with (
                self.subTest(
                    field=field_name,
                    value=value,
                ),
                self.assertRaises(ValueError),
            ):
                values = {
                    "high_percent": 85.0,
                    "critical_percent": 95.0,
                }
                values[field_name] = value

                UsageThresholdConfig(**values)

    def test_rejects_high_equal_to_critical(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "high_percent must be less than critical_percent",
        ):
            UsageThresholdConfig(
                high_percent=90.0,
                critical_percent=90.0,
            )

    def test_rejects_high_above_critical(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "high_percent must be less than critical_percent",
        ):
            UsageThresholdConfig(
                high_percent=95.0,
                critical_percent=90.0,
            )


class TemperatureThresholdConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = TemperatureThresholdConfig()

        self.assertEqual(
            config.high_celsius,
            75.0,
        )
        self.assertEqual(
            config.critical_celsius,
            85.0,
        )

    def test_normalizes_integer_values_to_float(
        self,
    ) -> None:
        config = TemperatureThresholdConfig(
            high_celsius=70,
            critical_celsius=80,
        )

        self.assertEqual(
            config.high_celsius,
            70.0,
        )
        self.assertEqual(
            config.critical_celsius,
            80.0,
        )

    def test_rejects_non_numeric_values(self) -> None:
        for field_name in (
            "high_celsius",
            "critical_celsius",
        ):
            for value in (
                True,
                "75",
                object(),
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(TypeError),
                ):
                    values = {
                        "high_celsius": 75.0,
                        "critical_celsius": 85.0,
                    }
                    values[field_name] = value

                    TemperatureThresholdConfig(
                        **values  # type: ignore[arg-type]
                    )

    def test_rejects_non_finite_values(self) -> None:
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(ValueError),
            ):
                TemperatureThresholdConfig(
                    high_celsius=value,
                )

    def test_rejects_high_equal_to_critical(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "high_celsius must be less than critical_celsius",
        ):
            TemperatureThresholdConfig(
                high_celsius=80.0,
                critical_celsius=80.0,
            )

    def test_rejects_high_above_critical(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "high_celsius must be less than critical_celsius",
        ):
            TemperatureThresholdConfig(
                high_celsius=90.0,
                critical_celsius=80.0,
            )


class LaunchpadConfigTests(unittest.TestCase):
    def test_default(self) -> None:
        self.assertTrue(LaunchpadConfig().enabled)

    def test_accepts_false(self) -> None:
        self.assertFalse(LaunchpadConfig(enabled=False).enabled)

    def test_rejects_non_boolean_enabled(
        self,
    ) -> None:
        for value in (
            1,
            0,
            "true",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "enabled must be a boolean",
                ),
            ):
                LaunchpadConfig(
                    enabled=value  # type: ignore[arg-type]
                )


class PlatformHealthConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = PlatformHealthConfig()

        self.assertIsInstance(
            config.temperature,
            TemperatureThresholdConfig,
        )
        self.assertIsInstance(
            config.memory,
            UsageThresholdConfig,
        )
        self.assertIsInstance(
            config.disk,
            UsageThresholdConfig,
        )
        self.assertEqual(
            config.disk_path,
            Path("/"),
        )
        self.assertEqual(
            config.ethernet_interface,
            "eth0",
        )
        self.assertEqual(
            config.wifi_interface,
            "wlan0",
        )

    def test_default_factories_create_distinct_objects(
        self,
    ) -> None:
        first = PlatformHealthConfig()
        second = PlatformHealthConfig()

        self.assertIsNot(
            first.temperature,
            second.temperature,
        )
        self.assertIsNot(
            first.memory,
            second.memory,
        )
        self.assertIsNot(
            first.disk,
            second.disk,
        )

    def test_normalizes_interface_names(self) -> None:
        config = PlatformHealthConfig(
            ethernet_interface=" eth0 ",
            wifi_interface=" wlan0 ",
        )

        self.assertEqual(
            config.ethernet_interface,
            "eth0",
        )
        self.assertEqual(
            config.wifi_interface,
            "wlan0",
        )

    def test_rejects_invalid_nested_types(
        self,
    ) -> None:
        cases = (
            (
                "temperature",
                "temperature must be a TemperatureThresholdConfig",
            ),
            (
                "memory",
                "memory must be a UsageThresholdConfig",
            ),
            (
                "disk",
                "disk must be a UsageThresholdConfig",
            ),
        )

        for field_name, message in cases:
            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    message,
                ),
            ):
                values = {
                    "temperature": (TemperatureThresholdConfig()),
                    "memory": UsageThresholdConfig(),
                    "disk": UsageThresholdConfig(),
                }
                values[field_name] = object()

                PlatformHealthConfig(
                    **values  # type: ignore[arg-type]
                )

    def test_rejects_invalid_disk_path_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "disk_path must be a Path",
        ):
            PlatformHealthConfig(
                disk_path="/"  # type: ignore[arg-type]
            )

    def test_rejects_blank_interfaces(self) -> None:
        for field_name in (
            "ethernet_interface",
            "wifi_interface",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaises(ValueError),
            ):
                values = {
                    "ethernet_interface": "eth0",
                    "wifi_interface": "wlan0",
                }
                values[field_name] = " "

                PlatformHealthConfig(**values)


class PlatformNetworkConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = PlatformNetworkConfig()

        self.assertEqual(
            config.local_host,
            "127.0.0.1",
        )
        self.assertEqual(
            config.bind_host,
            "0.0.0.0",
        )
        self.assertEqual(
            config.jupyterhub_port,
            8000,
        )
        self.assertEqual(
            config.vision_port,
            8080,
        )
        self.assertEqual(
            config.launchpad_port,
            8088,
        )
        self.assertEqual(
            config.wifi_fallback_delay_seconds,
            20,
        )

    def test_normalizes_string_values(self) -> None:
        config = PlatformNetworkConfig(
            local_host=" 127.0.0.1 ",
            bind_host=" 0.0.0.0 ",
            wifi_interface=" wlan0 ",
            ethernet_interface=" eth0 ",
            ap_connection_name=" PiAP ",
            identity_prefix=" Betabox ",
        )

        self.assertEqual(
            config.local_host,
            "127.0.0.1",
        )
        self.assertEqual(
            config.bind_host,
            "0.0.0.0",
        )
        self.assertEqual(
            config.ap_connection_name,
            "PiAP",
        )
        self.assertEqual(
            config.identity_prefix,
            "Betabox",
        )

    def test_urls(self) -> None:
        config = PlatformNetworkConfig()

        self.assertEqual(
            config.jupyterhub_url,
            "http://127.0.0.1:8000",
        )
        self.assertEqual(
            config.jupyterhub_health_url,
            "http://127.0.0.1:8000/hub/health",
        )
        self.assertEqual(
            config.vision_url,
            "http://127.0.0.1:8080",
        )
        self.assertEqual(
            config.launchpad_url,
            "http://127.0.0.1:8088",
        )
        self.assertEqual(
            config.launchpad_health_url,
            "http://127.0.0.1:8088/api/health",
        )
        self.assertEqual(
            config.launchpad_bind_address,
            (
                "0.0.0.0",
                8088,
            ),
        )

    def test_rejects_invalid_string_types(
        self,
    ) -> None:
        for field_name in (
            "local_host",
            "bind_host",
            "wifi_interface",
            "ethernet_interface",
            "ap_connection_name",
            "identity_prefix",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaises(TypeError),
            ):
                values = {
                    field_name: 123,
                }

                PlatformNetworkConfig(
                    **values  # type: ignore[arg-type]
                )

    def test_rejects_blank_strings(self) -> None:
        for field_name in (
            "local_host",
            "bind_host",
            "wifi_interface",
            "ethernet_interface",
            "ap_connection_name",
            "identity_prefix",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaises(ValueError),
            ):
                PlatformNetworkConfig(**{field_name: " "})

    def test_rejects_invalid_port_types(self) -> None:
        for field_name in (
            "jupyterhub_port",
            "vision_port",
            "launchpad_port",
        ):
            for value in (
                True,
                8080.0,
                "8080",
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(TypeError),
                ):
                    PlatformNetworkConfig(
                        **{
                            field_name: value,
                        }  # type: ignore[arg-type]
                    )

    def test_rejects_ports_outside_range(
        self,
    ) -> None:
        for field_name in (
            "jupyterhub_port",
            "vision_port",
            "launchpad_port",
        ):
            for value in (
                0,
                65536,
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(ValueError),
                ):
                    PlatformNetworkConfig(
                        **{
                            field_name: value,
                        }
                    )

    def test_rejects_invalid_fallback_delay_type(
        self,
    ) -> None:
        for value in (
            True,
            1.5,
            "20",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                PlatformNetworkConfig(
                    wifi_fallback_delay_seconds=value  # type: ignore[arg-type]
                )

    def test_rejects_negative_fallback_delay(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            PlatformNetworkConfig(wifi_fallback_delay_seconds=-1)


class ServiceDefinitionTests(unittest.TestCase):
    def test_create(self) -> None:
        service = ServiceDefinition(
            unit="example.service",
            display_name="Example",
            description="An example service.",
            category=ServiceCategory.WEB,
            startup=ServiceStartup.CONTINUOUS,
        )

        self.assertEqual(
            service.unit,
            "example.service",
        )
        self.assertEqual(
            service.category,
            ServiceCategory.WEB,
        )
        self.assertEqual(
            service.startup,
            ServiceStartup.CONTINUOUS,
        )

    def test_normalizes_strings(self) -> None:
        service = ServiceDefinition(
            unit=" example.service ",
            display_name=" Example ",
            description=" Description ",
            category=ServiceCategory.WEB,
            startup=ServiceStartup.CONTINUOUS,
        )

        self.assertEqual(
            service.unit,
            "example.service",
        )
        self.assertEqual(
            service.display_name,
            "Example",
        )
        self.assertEqual(
            service.description,
            "Description",
        )

    def test_rejects_invalid_string_types(
        self,
    ) -> None:
        for field_name in (
            "unit",
            "display_name",
            "description",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaises(TypeError),
            ):
                values = {
                    "unit": "example.service",
                    "display_name": "Example",
                    "description": "Description",
                    "category": ServiceCategory.WEB,
                    "startup": (ServiceStartup.CONTINUOUS),
                }
                values[field_name] = 123

                ServiceDefinition(
                    **values  # type: ignore[arg-type]
                )

    def test_rejects_blank_strings(self) -> None:
        for field_name in (
            "unit",
            "display_name",
            "description",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaises(ValueError),
            ):
                values = {
                    "unit": "example.service",
                    "display_name": "Example",
                    "description": "Description",
                    "category": ServiceCategory.WEB,
                    "startup": (ServiceStartup.CONTINUOUS),
                }
                values[field_name] = " "

                ServiceDefinition(**values)

    def test_rejects_invalid_category(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "category must be a ServiceCategory",
        ):
            ServiceDefinition(
                unit="example.service",
                display_name="Example",
                description="Description",
                category="web",  # type: ignore[arg-type]
                startup=ServiceStartup.CONTINUOUS,
            )

    def test_rejects_invalid_startup(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "startup must be a ServiceStartup",
        ):
            ServiceDefinition(
                unit="example.service",
                display_name="Example",
                description="Description",
                category=ServiceCategory.WEB,
                startup="continuous",  # type: ignore[arg-type]
            )


class PlatformServicesConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = PlatformServicesConfig()

        self.assertEqual(
            len(config.all_services),
            8,
        )
        self.assertEqual(
            config.hostname.unit,
            "set-hostname-from-serial.service",
        )
        self.assertEqual(
            config.video.unit,
            "betabox-video.service",
        )
        self.assertEqual(
            config.launchpad.unit,
            "betabox-launchpad.service",
        )

    def test_all_units(self) -> None:
        config = PlatformServicesConfig()

        self.assertEqual(
            config.all_units,
            tuple(service.unit for service in config.all_services),
        )
        self.assertEqual(
            len(config.all_units),
            len(set(config.all_units)),
        )

    def test_get_returns_configured_service(
        self,
    ) -> None:
        config = PlatformServicesConfig()

        self.assertIs(
            config.get("betabox-video.service"),
            config.video,
        )

    def test_get_normalizes_unit(self) -> None:
        config = PlatformServicesConfig()

        self.assertIs(
            config.get(" betabox-video.service "),
            config.video,
        )

    def test_get_returns_none_for_unknown_unit(
        self,
    ) -> None:
        config = PlatformServicesConfig()

        self.assertIsNone(config.get("unknown.service"))

    def test_get_rejects_invalid_unit(self) -> None:
        for value in (
            123,
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                PlatformServicesConfig().get(
                    value  # type: ignore[arg-type]
                )

        with self.assertRaises(ValueError):
            PlatformServicesConfig().get(" ")

    def test_rejects_invalid_service_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "video must be a ServiceDefinition",
        ):
            PlatformServicesConfig(
                video=object()  # type: ignore[arg-type]
            )

    def test_rejects_duplicate_units(self) -> None:
        defaults = PlatformServicesConfig()

        duplicate_video = replace(
            defaults.video,
            unit=defaults.monitor.unit,
        )

        with self.assertRaisesRegex(
            ValueError,
            "service unit names must be unique",
        ):
            PlatformServicesConfig(
                video=duplicate_video,
            )


class PlatformVerificationConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = PlatformVerificationConfig()

        self.assertEqual(
            config.i2c_device,
            Path("/dev/i2c-1"),
        )
        self.assertEqual(
            config.i2c_bus,
            1,
        )
        self.assertEqual(
            config.boot_config_file,
            Path("/boot/firmware/config.txt"),
        )
        self.assertEqual(
            config.command_timeout_seconds,
            5,
        )

    def test_rejects_invalid_path_types(
        self,
    ) -> None:
        for field_name in (
            "i2c_device",
            "boot_config_file",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaises(TypeError),
            ):
                PlatformVerificationConfig(
                    **{
                        field_name: "/path",
                    }  # type: ignore[arg-type]
                )

    def test_rejects_invalid_i2c_bus_type(
        self,
    ) -> None:
        for value in (
            True,
            1.0,
            "1",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                PlatformVerificationConfig(
                    i2c_bus=value  # type: ignore[arg-type]
                )

    def test_rejects_negative_i2c_bus(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            PlatformVerificationConfig(i2c_bus=-1)

    def test_rejects_invalid_timeout_type(
        self,
    ) -> None:
        for value in (
            True,
            5.0,
            "5",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                PlatformVerificationConfig(
                    command_timeout_seconds=value  # type: ignore[arg-type]
                )

    def test_rejects_non_positive_timeout(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            PlatformVerificationConfig(command_timeout_seconds=0)

    def test_normalizes_string_tuples(self) -> None:
        config = PlatformVerificationConfig(
            required_python_modules=(
                " cv2 ",
                " numpy ",
            ),
        )

        self.assertEqual(
            config.required_python_modules,
            (
                "cv2",
                "numpy",
            ),
        )

    def test_rejects_non_tuple_collections(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            PlatformVerificationConfig(
                required_executables=[  # type: ignore[arg-type]
                    "node",
                ]
            )

    def test_rejects_invalid_tuple_items(
        self,
    ) -> None:
        for value in (
            (
                "node",
                123,
            ),
            (
                "node",
                " ",
            ),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(
                    (
                        TypeError,
                        ValueError,
                    )
                ),
            ):
                PlatformVerificationConfig(
                    required_executables=value  # type: ignore[arg-type]
                )


class PlatformMonitoringConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = PlatformMonitoringConfig()

        self.assertEqual(
            config.interval_seconds,
            60,
        )
        self.assertEqual(
            config.default_event_count,
            20,
        )
        self.assertEqual(
            config.default_log_lines,
            50,
        )

    def test_rejects_invalid_types(self) -> None:
        for field_name in (
            "interval_seconds",
            "default_event_count",
            "default_log_lines",
        ):
            for value in (
                True,
                1.0,
                "1",
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(TypeError),
                ):
                    PlatformMonitoringConfig(
                        **{
                            field_name: value,
                        }  # type: ignore[arg-type]
                    )

    def test_rejects_non_positive_interval(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            PlatformMonitoringConfig(interval_seconds=0)

    def test_allows_zero_event_count(self) -> None:
        config = PlatformMonitoringConfig(default_event_count=0)

        self.assertEqual(
            config.default_event_count,
            0,
        )

    def test_rejects_negative_event_count(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            PlatformMonitoringConfig(default_event_count=-1)

    def test_rejects_non_positive_log_lines(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            PlatformMonitoringConfig(default_log_lines=0)


class PlatformRuntimeConfigTests(unittest.TestCase):
    def test_default(self) -> None:
        self.assertEqual(
            PlatformRuntimeConfig().vision_fps,
            20,
        )

    def test_rejects_invalid_fps_type(self) -> None:
        for value in (
            True,
            20.0,
            "20",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(TypeError),
            ):
                PlatformRuntimeConfig(
                    vision_fps=value  # type: ignore[arg-type]
                )

    def test_rejects_non_positive_fps(
        self,
    ) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(ValueError),
            ):
                PlatformRuntimeConfig(vision_fps=value)


class PlatformConfigTests(unittest.TestCase):
    def test_default(self) -> None:
        with patch(
            "betabox_robotics.config.platform.Path.home",
            return_value=Path("/home/picar"),
        ):
            config = PlatformConfig.default()

        self.assertIsInstance(
            config.paths,
            PlatformPathsConfig,
        )
        self.assertIsInstance(
            config.health,
            PlatformHealthConfig,
        )
        self.assertIsInstance(
            config.network,
            PlatformNetworkConfig,
        )
        self.assertIsInstance(
            config.services,
            PlatformServicesConfig,
        )
        self.assertIsInstance(
            config.verification,
            PlatformVerificationConfig,
        )
        self.assertIsInstance(
            config.monitoring,
            PlatformMonitoringConfig,
        )
        self.assertIsInstance(
            config.runtime,
            PlatformRuntimeConfig,
        )
        self.assertIsInstance(
            config.launchpad,
            LaunchpadConfig,
        )
        self.assertEqual(
            config.paths.home,
            Path("/home/picar"),
        )

    def test_rejects_invalid_nested_types(
        self,
    ) -> None:
        valid = PlatformConfig.default()

        cases = (
            (
                "paths",
                PlatformPathsConfig,
            ),
            (
                "health",
                PlatformHealthConfig,
            ),
            (
                "network",
                PlatformNetworkConfig,
            ),
            (
                "services",
                PlatformServicesConfig,
            ),
            (
                "verification",
                PlatformVerificationConfig,
            ),
            (
                "monitoring",
                PlatformMonitoringConfig,
            ),
            (
                "runtime",
                PlatformRuntimeConfig,
            ),
            (
                "launchpad",
                LaunchpadConfig,
            ),
        )

        for field_name, expected_type in cases:
            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    (f"{field_name} must be a {expected_type.__name__}"),
                ),
            ):
                values = {
                    "paths": valid.paths,
                    "health": valid.health,
                    "network": valid.network,
                    "services": valid.services,
                    "verification": (valid.verification),
                    "monitoring": valid.monitoring,
                    "runtime": valid.runtime,
                    "launchpad": valid.launchpad,
                }
                values[field_name] = object()

                PlatformConfig(
                    **values  # type: ignore[arg-type]
                )

    def test_default_platform_config(self) -> None:
        self.assertIsInstance(
            DEFAULT_PLATFORM_CONFIG,
            PlatformConfig,
        )

    def test_configs_are_frozen(self) -> None:
        config = PlatformRuntimeConfig()

        with self.assertRaises(FrozenInstanceError):
            config.vision_fps = 30  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
