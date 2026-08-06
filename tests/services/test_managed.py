from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.managed import (
    MANAGED_SERVICES,
    ManagedService,
    _validate_optional_path,
    _validate_string,
    managed_services,
)


class ValidateStringTests(unittest.TestCase):
    def test_accepts_and_normalizes_string(self) -> None:
        self.assertEqual(
            _validate_string(
                " Video Service ",
                name="title",
            ),
            "Video Service",
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
                    "title must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="title",
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
                    "title cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="title",
                )


class ValidateOptionalPathTests(unittest.TestCase):
    def test_accepts_none(self) -> None:
        self.assertIsNone(
            _validate_optional_path(
                None,
                name="log_file",
            )
        )

    def test_accepts_path(self) -> None:
        path = Path("/var/log/betabox/video.log")

        self.assertEqual(
            _validate_optional_path(
                path,
                name="log_file",
            ),
            path,
        )

    def test_accepts_string(self) -> None:
        self.assertEqual(
            _validate_optional_path(
                "/var/log/betabox/video.log",
                name="log_file",
            ),
            Path("/var/log/betabox/video.log"),
        )

    def test_expands_user_directory(self) -> None:
        with patch(
            "betabox_robotics.services.managed.Path.expanduser",
            return_value=Path("/home/picar/video.log"),
        ):
            result = _validate_optional_path(
                "~/video.log",
                name="log_file",
            )

        self.assertEqual(
            result,
            Path("/home/picar/video.log"),
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            123,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "log_file must be a string, Path, or None",
                ),
            ):
                _validate_optional_path(
                    value,
                    name="log_file",
                )


class ManagedServiceTests(unittest.TestCase):
    def test_create(self) -> None:
        log_file = Path("/var/log/betabox/video.log")

        service = ManagedService(
            name="video",
            title="Video Service",
            unit="betabox-video.service",
            log_file=log_file,
        )

        self.assertEqual(
            service.name,
            "video",
        )
        self.assertEqual(
            service.title,
            "Video Service",
        )
        self.assertEqual(
            service.unit,
            "betabox-video.service",
        )
        self.assertEqual(
            service.log_file,
            log_file,
        )

    def test_normalizes_values(self) -> None:
        service = ManagedService(
            name=" video ",
            title=" Video Service ",
            unit=" betabox-video.service ",
            log_file="/var/log/video.log",
        )

        self.assertEqual(
            service.name,
            "video",
        )
        self.assertEqual(
            service.title,
            "Video Service",
        )
        self.assertEqual(
            service.unit,
            "betabox-video.service",
        )
        self.assertEqual(
            service.log_file,
            Path("/var/log/video.log"),
        )

    def test_log_file_defaults_to_none(self) -> None:
        service = ManagedService(
            name="hostname",
            title="Hostname Service",
            unit="set-hostname-from-serial.service",
        )

        self.assertIsNone(service.log_file)

    def test_rejects_invalid_strings(self) -> None:
        fields = (
            "name",
            "title",
            "unit",
        )

        for field_name in fields:
            values: dict[str, object] = {
                "name": "video",
                "title": "Video Service",
                "unit": "betabox-video.service",
            }
            values[field_name] = " "

            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    ValueError,
                    f"{field_name} cannot be empty",
                ),
            ):
                ManagedService(
                    **values  # type: ignore[arg-type]
                )

    def test_is_frozen(self) -> None:
        service = ManagedService(
            name="video",
            title="Video Service",
            unit="betabox-video.service",
        )

        with self.assertRaises(FrozenInstanceError):
            service.name = "changed"  # type: ignore[misc]


class ManagedServicesTests(unittest.TestCase):
    def test_expected_service_keys(self) -> None:
        services = managed_services()

        self.assertEqual(
            tuple(services),
            (
                "hostname",
                "boot-announce",
                "monitor",
                "jupyterhub",
                "video",
                "wifi-fallback",
                "guest-reset",
                "launchpad",
            ),
        )

    def test_service_names_match_mapping_keys(self) -> None:
        services = managed_services()

        for name, service in services.items():
            with self.subTest(name=name):
                self.assertEqual(
                    service.name,
                    name,
                )

    def test_uses_default_platform_service_values(self) -> None:
        services = managed_services()
        config_services = DEFAULT_PLATFORM_CONFIG.services

        expected_units = {
            "hostname": (config_services.hostname.unit),
            "boot-announce": (config_services.boot_announce.unit),
            "monitor": (config_services.monitor.unit),
            "jupyterhub": (config_services.jupyterhub.unit),
            "video": (config_services.video.unit),
            "wifi-fallback": (config_services.wifi_fallback.unit),
            "guest-reset": (config_services.guest_reset.unit),
            "launchpad": (config_services.launchpad.unit),
        }

        for name, expected_unit in expected_units.items():
            with self.subTest(name=name):
                self.assertEqual(
                    services[name].unit,
                    expected_unit,
                )

    def test_uses_default_display_names(self) -> None:
        services = managed_services()
        config_services = DEFAULT_PLATFORM_CONFIG.services

        expected_titles = {
            "hostname": (config_services.hostname.display_name),
            "boot-announce": (config_services.boot_announce.display_name),
            "monitor": (config_services.monitor.display_name),
            "jupyterhub": (config_services.jupyterhub.display_name),
            "video": (config_services.video.display_name),
            "wifi-fallback": (config_services.wifi_fallback.display_name),
            "guest-reset": (config_services.guest_reset.display_name),
            "launchpad": (config_services.launchpad.display_name),
        }

        for name, expected_title in expected_titles.items():
            with self.subTest(name=name):
                self.assertEqual(
                    services[name].title,
                    expected_title,
                )

    def test_assigns_expected_log_files(self) -> None:
        services = managed_services()
        paths = DEFAULT_PLATFORM_CONFIG.paths

        self.assertEqual(
            services["boot-announce"].log_file,
            paths.boot_announce_log,
        )
        self.assertEqual(
            services["monitor"].log_file,
            paths.monitor_log,
        )
        self.assertEqual(
            services["video"].log_file,
            paths.video_log,
        )

        for name in (
            "hostname",
            "jupyterhub",
            "wifi-fallback",
            "guest-reset",
            "launchpad",
        ):
            with self.subTest(name=name):
                self.assertIsNone(services[name].log_file)

    def test_returns_fresh_dictionary(self) -> None:
        first = managed_services()
        second = managed_services()

        self.assertIsNot(
            first,
            second,
        )
        self.assertEqual(
            first,
            second,
        )

        first.pop("video")

        self.assertIn(
            "video",
            second,
        )

    def test_rejects_invalid_config(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "config must be a PlatformConfig",
        ):
            managed_services(
                object()  # type: ignore[arg-type]
            )


class ManagedServicesConstantTests(unittest.TestCase):
    def test_is_mapping_proxy(self) -> None:
        self.assertIsInstance(
            MANAGED_SERVICES,
            MappingProxyType,
        )

    def test_matches_default_mapping(self) -> None:
        self.assertEqual(
            dict(MANAGED_SERVICES),
            managed_services(),
        )

    def test_cannot_add_service(self) -> None:
        with self.assertRaises(TypeError):
            MANAGED_SERVICES["new-service"] = ManagedService(  # type: ignore[index]
                name="new-service",
                title="New Service",
                unit="new.service",
            )

    def test_cannot_remove_service(self) -> None:
        with self.assertRaises(TypeError):
            del MANAGED_SERVICES["video"]  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
