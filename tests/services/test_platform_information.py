from __future__ import annotations

import shutil
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.platform_information import (
    FeatureInformation,
    MediaLocationInformation,
    NetworkInformation,
    PlatformInformationReport,
    RobotInformation,
    SoftwareInformation,
    StorageInformation,
    _validate_config,
    _validate_flag,
    _validate_path,
    _validate_port,
    _validate_string,
    collect_platform_information,
    collect_storage_information,
    directory_available,
    operating_system_name,
    public_urls,
    robot_identifier,
)
from betabox_robotics.version import __version__

MODULE = "betabox_robotics.services.platform_information"


def make_robot_information(
    *,
    model: str = "Betabox Car",
    hostname: str = "Betabox-7eea",
    identifier: str | None = "7eea",
    control_available: bool = True,
) -> RobotInformation:
    return RobotInformation(
        model=model,
        hostname=hostname,
        identifier=identifier,
        control_available=control_available,
    )


def make_network_information(
    *,
    hostname: str = "Betabox-7eea",
    ip_addresses: tuple[str, ...] = ("192.168.1.25",),
    launchpad_urls: tuple[str, ...] = (
        "http://Betabox-7eea.local:8080",
        "http://192.168.1.25:8080",
    ),
    jupyterhub_urls: tuple[str, ...] = (
        "http://Betabox-7eea.local:8000",
        "http://192.168.1.25:8000",
    ),
    vision_urls: tuple[str, ...] = (
        "http://Betabox-7eea.local:5000",
        "http://192.168.1.25:5000",
    ),
) -> NetworkInformation:
    return NetworkInformation(
        hostname=hostname,
        ip_addresses=ip_addresses,
        launchpad_urls=launchpad_urls,
        jupyterhub_urls=jupyterhub_urls,
        vision_urls=vision_urls,
    )


def make_software_information(
    *,
    betabox_robotics_version: str = "1.0.0",
    python_version: str = "3.11.2",
    operating_system: str = "Linux 6.12",
    architecture: str = "aarch64",
) -> SoftwareInformation:
    return SoftwareInformation(
        betabox_robotics_version=(betabox_robotics_version),
        python_version=python_version,
        operating_system=operating_system,
        architecture=architecture,
    )


def make_storage_information(
    *,
    total_bytes: int = 1000,
    used_bytes: int = 400,
    available_bytes: int = 600,
    used_percent: float = 40.0,
) -> StorageInformation:
    return StorageInformation(
        total_bytes=total_bytes,
        used_bytes=used_bytes,
        available_bytes=available_bytes,
        used_percent=used_percent,
    )


def make_media_information(
    *,
    pictures_available: bool = True,
    videos_available: bool = True,
    sounds_available: bool = True,
) -> MediaLocationInformation:
    return MediaLocationInformation(
        pictures_available=pictures_available,
        videos_available=videos_available,
        sounds_available=sounds_available,
    )


def make_feature_information(
    *,
    vision_service_available: bool = True,
    camera_ready: bool = True,
    jupyterhub_available: bool = True,
) -> FeatureInformation:
    return FeatureInformation(
        vision_service_available=(vision_service_available),
        camera_ready=camera_ready,
        jupyterhub_available=(jupyterhub_available),
    )


def make_report() -> PlatformInformationReport:
    return PlatformInformationReport(
        robot=make_robot_information(),
        network=make_network_information(),
        software=make_software_information(),
        storage=make_storage_information(),
        media=make_media_information(),
        features=make_feature_information(),
    )


def make_summary(
    *,
    hostname: str = "Betabox-7eea",
    ip_addresses: list[str] | None = None,
    control_available: bool = True,
    vision_service_available: bool = True,
    vision_camera_running: bool = True,
    vision_camera_has_frame: bool = True,
    jupyterhub_proxy_available: bool = True,
) -> SimpleNamespace:
    if ip_addresses is None:
        ip_addresses = [
            "192.168.1.25",
        ]

    vision = SimpleNamespace(
        service_available=(vision_service_available),
        camera_running=(vision_camera_running),
        camera_has_frame=(vision_camera_has_frame),
    )

    return SimpleNamespace(
        hostname=hostname,
        ip_addresses=ip_addresses,
        control=SimpleNamespace(
            available=control_available,
        ),
        hardware=SimpleNamespace(
            vision=vision,
        ),
        jupyterhub_proxy_available=(jupyterhub_proxy_available),
    )


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_config(
        self,
    ) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_validate_config_rejects_invalid_value(
        self,
    ) -> None:
        for value in (
            None,
            object(),
            "config",
            123,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("config must be a PlatformConfig"),
                ),
            ):
                _validate_config(value)

    def test_validate_string_strips_value(
        self,
    ) -> None:
        self.assertEqual(
            _validate_string(
                " Betabox ",
                name="model",
            ),
            "Betabox",
        )

    def test_validate_string_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "model must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="model",
                )

    def test_validate_string_rejects_empty_value(
        self,
    ) -> None:
        for value in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "model cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="model",
                )

    def test_validate_path_accepts_path(
        self,
    ) -> None:
        path = Path("/")

        self.assertEqual(
            _validate_path(
                path,
                name="path",
            ),
            path,
        )

    def test_validate_path_accepts_string(
        self,
    ) -> None:
        self.assertEqual(
            _validate_path(
                " / ",
                name="path",
            ),
            Path("/"),
        )

    def test_validate_path_expands_user(
        self,
    ) -> None:
        expanded = Path("/home/picar/media")

        with patch.object(
            Path,
            "expanduser",
            return_value=expanded,
        ) as expanduser:
            result = _validate_path(
                "~/media",
                name="path",
            )

        expanduser.assert_called_once_with()
        self.assertEqual(
            result,
            expanded,
        )

    def test_validate_path_rejects_boolean(
        self,
    ) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("path must be a string or Path"),
                ),
            ):
                _validate_path(
                    value,
                    name="path",
                )

    def test_validate_path_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("path must be a string or Path"),
        ):
            _validate_path(
                object(),
                name="path",
            )

    def test_validate_path_rejects_empty_string(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path cannot be empty",
        ):
            _validate_path(
                " ",
                name="path",
            )

    def test_validate_port_accepts_valid_port(
        self,
    ) -> None:
        for value in (
            1,
            80,
            8080,
            65535,
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    _validate_port(value),
                    value,
                )

    def test_validate_port_rejects_boolean(
        self,
    ) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("port must be an integer"),
                ),
            ):
                _validate_port(value)

    def test_validate_port_rejects_invalid_type(
        self,
    ) -> None:
        for value in (
            None,
            80.0,
            "80",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("port must be an integer"),
                ),
            ):
                _validate_port(value)

    def test_validate_port_rejects_out_of_range(
        self,
    ) -> None:
        for value in (
            0,
            -1,
            65536,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("port must be between 1 and 65535"),
                ),
            ):
                _validate_port(value)

    def test_validate_flag_accepts_boolean(
        self,
    ) -> None:
        self.assertTrue(
            _validate_flag(
                True,
                name="available",
            )
        )
        self.assertFalse(
            _validate_flag(
                False,
                name="available",
            )
        )

    def test_validate_flag_rejects_non_boolean(
        self,
    ) -> None:
        for value in (
            None,
            0,
            1,
            "true",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("available must be a boolean"),
                ),
            ):
                _validate_flag(
                    value,
                    name="available",
                )


class RobotInformationTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        value = make_robot_information()

        self.assertEqual(
            value.model,
            "Betabox Car",
        )
        self.assertEqual(
            value.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            value.identifier,
            "7eea",
        )
        self.assertTrue(value.control_available)

    def test_strips_string_values(self) -> None:
        value = make_robot_information(
            model=" Betabox Car ",
            hostname=" Betabox-7eea ",
            identifier=" 7eea ",
        )

        self.assertEqual(
            value.model,
            "Betabox Car",
        )
        self.assertEqual(
            value.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            value.identifier,
            "7eea",
        )

    def test_accepts_missing_identifier(
        self,
    ) -> None:
        value = make_robot_information(identifier=None)

        self.assertIsNone(value.identifier)

    def test_rejects_empty_identifier(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "identifier cannot be empty",
        ):
            make_robot_information(identifier=" ")

    def test_rejects_invalid_boolean(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("control_available must be a boolean"),
        ):
            make_robot_information(
                control_available=1,  # type: ignore[arg-type]
            )

    def test_is_frozen(self) -> None:
        value = make_robot_information()

        with self.assertRaises(FrozenInstanceError):
            value.hostname = "changed"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        self.assertFalse(
            hasattr(
                make_robot_information(),
                "__dict__",
            )
        )


class NetworkInformationTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        value = make_network_information()

        self.assertEqual(
            value.ip_addresses,
            ("192.168.1.25",),
        )

    def test_strips_tuple_items(self) -> None:
        value = make_network_information(
            ip_addresses=(" 192.168.1.25 ",),
            launchpad_urls=(" http://robot.local:8080 ",),
            jupyterhub_urls=(" http://robot.local:8000 ",),
            vision_urls=(" http://robot.local:5000 ",),
        )

        self.assertEqual(
            value.ip_addresses,
            ("192.168.1.25",),
        )
        self.assertEqual(
            value.launchpad_urls,
            ("http://robot.local:8080",),
        )

    def test_accepts_empty_tuples(self) -> None:
        value = make_network_information(
            ip_addresses=(),
            launchpad_urls=(),
            jupyterhub_urls=(),
            vision_urls=(),
        )

        self.assertEqual(
            value.ip_addresses,
            (),
        )

    def test_rejects_list_value(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("ip_addresses must be a tuple"),
        ):
            make_network_information(
                ip_addresses=[  # type: ignore[arg-type]
                    "192.168.1.25"
                ]
            )

    def test_rejects_empty_tuple_item(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("ip_addresses item cannot be empty"),
        ):
            make_network_information(ip_addresses=(" ",))

    def test_is_frozen_and_slotted(
        self,
    ) -> None:
        value = make_network_information()

        self.assertFalse(hasattr(value, "__dict__"))

        with self.assertRaises(FrozenInstanceError):
            value.hostname = "changed"  # type: ignore[misc]


class SoftwareInformationTests(unittest.TestCase):
    def test_strips_all_fields(self) -> None:
        value = make_software_information(
            betabox_robotics_version=" 1.0.0 ",
            python_version=" 3.11 ",
            operating_system=" Linux ",
            architecture=" aarch64 ",
        )

        self.assertEqual(
            value.betabox_robotics_version,
            "1.0.0",
        )
        self.assertEqual(
            value.python_version,
            "3.11",
        )
        self.assertEqual(
            value.operating_system,
            "Linux",
        )
        self.assertEqual(
            value.architecture,
            "aarch64",
        )

    def test_rejects_empty_field(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("architecture cannot be empty"),
        ):
            make_software_information(architecture=" ")

    def test_is_frozen_and_slotted(
        self,
    ) -> None:
        value = make_software_information()

        self.assertFalse(hasattr(value, "__dict__"))

        with self.assertRaises(FrozenInstanceError):
            value.architecture = "x86"  # type: ignore[misc]


class StorageInformationTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        value = make_storage_information()

        self.assertEqual(
            value.used_percent,
            40.0,
        )

    def test_converts_integer_percent_to_float(
        self,
    ) -> None:
        value = make_storage_information(
            used_percent=40,  # type: ignore[arg-type]
        )

        self.assertIsInstance(
            value.used_percent,
            float,
        )
        self.assertEqual(
            value.used_percent,
            40.0,
        )

    def test_rejects_boolean_byte_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("total_bytes must be an integer"),
        ):
            make_storage_information(
                total_bytes=True,  # type: ignore[arg-type]
            )

    def test_rejects_negative_byte_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("used_bytes cannot be negative"),
        ):
            make_storage_information(used_bytes=-1)

    def test_rejects_invalid_percent_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("used_percent must be a number"),
        ):
            make_storage_information(
                used_percent="40",  # type: ignore[arg-type]
            )

    def test_rejects_percent_out_of_range(
        self,
    ) -> None:
        for value in (
            -0.1,
            100.1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    ("used_percent must be between 0.0 and 100.0"),
                ),
            ):
                make_storage_information(used_percent=value)

    def test_is_frozen_and_slotted(
        self,
    ) -> None:
        value = make_storage_information()

        self.assertFalse(hasattr(value, "__dict__"))

        with self.assertRaises(FrozenInstanceError):
            value.total_bytes = 0  # type: ignore[misc]


class AvailabilityModelTests(unittest.TestCase):
    def test_media_information_accepts_booleans(
        self,
    ) -> None:
        value = make_media_information(videos_available=False)

        self.assertFalse(value.videos_available)

    def test_media_information_rejects_non_boolean(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("pictures_available must be a boolean"),
        ):
            make_media_information(
                pictures_available=1,  # type: ignore[arg-type]
            )

    def test_feature_information_accepts_booleans(
        self,
    ) -> None:
        value = make_feature_information(camera_ready=False)

        self.assertFalse(value.camera_ready)

    def test_feature_information_rejects_non_boolean(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("camera_ready must be a boolean"),
        ):
            make_feature_information(
                camera_ready=1,  # type: ignore[arg-type]
            )


class PlatformInformationReportTests(unittest.TestCase):
    def test_accepts_valid_models(self) -> None:
        report = make_report()

        self.assertIsInstance(
            report.robot,
            RobotInformation,
        )

    def test_rejects_invalid_nested_model(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("robot must be a RobotInformation"),
        ):
            PlatformInformationReport(
                robot=object(),  # type: ignore[arg-type]
                network=make_network_information(),
                software=make_software_information(),
                storage=make_storage_information(),
                media=make_media_information(),
                features=make_feature_information(),
            )

    def test_to_dict_returns_nested_dictionary(
        self,
    ) -> None:
        report = make_report()

        result = report.to_dict()

        self.assertEqual(
            result["robot"]["hostname"],
            "Betabox-7eea",
        )
        self.assertEqual(
            result["network"]["ip_addresses"],
            ("192.168.1.25",),
        )
        self.assertEqual(
            result["storage"]["used_percent"],
            40.0,
        )

    def test_to_dict_returns_independent_values(
        self,
    ) -> None:
        report = make_report()

        first = report.to_dict()
        second = report.to_dict()

        self.assertIsNot(
            first,
            second,
        )
        self.assertIsNot(
            first["robot"],
            second["robot"],
        )


class RobotIdentifierTests(unittest.TestCase):
    def test_extracts_identifier(self) -> None:
        self.assertEqual(
            robot_identifier(
                "Betabox-7eea",
                prefix="Betabox",
            ),
            "7eea",
        )

    def test_is_case_insensitive(self) -> None:
        self.assertEqual(
            robot_identifier(
                "BETABOX-7eea",
                prefix="betabox",
            ),
            "7eea",
        )

    def test_strips_inputs_and_identifier(
        self,
    ) -> None:
        self.assertEqual(
            robot_identifier(
                " Betabox-7eea ",
                prefix=" Betabox ",
            ),
            "7eea",
        )

    def test_returns_none_for_wrong_prefix(
        self,
    ) -> None:
        self.assertIsNone(
            robot_identifier(
                "Robot-7eea",
                prefix="Betabox",
            )
        )

    def test_returns_none_for_empty_identifier(
        self,
    ) -> None:
        self.assertIsNone(
            robot_identifier(
                "Betabox-",
                prefix="Betabox",
            )
        )

    def test_rejects_empty_hostname(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "hostname cannot be empty",
        ):
            robot_identifier(
                " ",
                prefix="Betabox",
            )


class PublicUrlsTests(unittest.TestCase):
    def test_builds_hostname_and_ip_urls(
        self,
    ) -> None:
        result = public_urls(
            hostname="Betabox-7eea",
            ip_addresses=[
                "192.168.1.25",
            ],
            port=8080,
        )

        self.assertEqual(
            result,
            (
                "http://Betabox-7eea.local:8080",
                "http://192.168.1.25:8080",
            ),
        )

    def test_does_not_duplicate_local_suffix(
        self,
    ) -> None:
        result = public_urls(
            hostname="Betabox-7eea.local",
            ip_addresses=[],
            port=8080,
        )

        self.assertEqual(
            result,
            ("http://Betabox-7eea.local:8080",),
        )

    def test_local_suffix_check_is_case_insensitive(
        self,
    ) -> None:
        result = public_urls(
            hostname="BETABOX.LOCAL",
            ip_addresses=[],
            port=8080,
        )

        self.assertEqual(
            result,
            ("http://BETABOX.LOCAL:8080",),
        )

    def test_deduplicates_addresses(
        self,
    ) -> None:
        result = public_urls(
            hostname="Betabox-7eea",
            ip_addresses=[
                "192.168.1.25",
                "192.168.1.25",
            ],
            port=8080,
        )

        self.assertEqual(
            result.count("http://192.168.1.25:8080"),
            1,
        )

    def test_filters_bind_and_loopback_addresses(
        self,
    ) -> None:
        result = public_urls(
            hostname="Betabox-7eea",
            ip_addresses=[
                "0.0.0.0",
                "127.0.0.1",
                "::",
                "::1",
            ],
            port=8080,
        )

        self.assertEqual(
            result,
            ("http://Betabox-7eea.local:8080",),
        )

    def test_formats_ipv6_with_brackets(
        self,
    ) -> None:
        result = public_urls(
            hostname="Betabox-7eea",
            ip_addresses=[
                "2001:db8::1",
            ],
            port=8080,
        )

        self.assertEqual(
            result[-1],
            "http://[2001:db8::1]:8080",
        )

    def test_rejects_invalid_address_collection(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("ip_addresses must be a list or tuple"),
        ):
            public_urls(
                hostname="Betabox",
                ip_addresses="192.168.1.25",  # type: ignore[arg-type]
                port=8080,
            )

    def test_rejects_empty_address_item(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("ip address cannot be empty"),
        ):
            public_urls(
                hostname="Betabox",
                ip_addresses=[
                    " ",
                ],
                port=8080,
            )


class CollectStorageInformationTests(unittest.TestCase):
    def test_collects_and_calculates_usage(
        self,
    ) -> None:
        usage = shutil._ntuple_diskusage(
            total=1000,
            used=333,
            free=667,
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=usage,
        ) as disk_usage:
            result = collect_storage_information(" / ")

        disk_usage.assert_called_once_with(Path("/"))
        self.assertEqual(
            result,
            StorageInformation(
                total_bytes=1000,
                used_bytes=333,
                available_bytes=667,
                used_percent=33.3,
            ),
        )

    def test_zero_total_reports_zero_percent(
        self,
    ) -> None:
        usage = shutil._ntuple_diskusage(
            total=0,
            used=0,
            free=0,
        )

        with patch(
            f"{MODULE}.shutil.disk_usage",
            return_value=usage,
        ):
            result = collect_storage_information("/")

        self.assertEqual(
            result.used_percent,
            0.0,
        )

    def test_os_error_returns_empty_information(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.shutil.disk_usage",
            side_effect=OSError("unavailable"),
        ):
            result = collect_storage_information("/")

        self.assertEqual(
            result,
            StorageInformation(
                total_bytes=0,
                used_bytes=0,
                available_bytes=0,
                used_percent=0.0,
            ),
        )

    def test_unexpected_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.shutil.disk_usage",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_storage_information("/")

        self.assertIs(
            context.exception,
            error,
        )


class DirectoryAvailableTests(unittest.TestCase):
    def test_returns_true_for_directory(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=True,
            ),
        ):
            result = directory_available("/home/student/media")

        self.assertTrue(result)

    def test_returns_false_for_missing_path(
        self,
    ) -> None:
        with (
            patch.object(
                Path,
                "exists",
                return_value=False,
            ),
            patch.object(Path, "is_dir") as is_dir,
        ):
            result = directory_available("/missing")

        self.assertFalse(result)
        is_dir.assert_not_called()

    def test_returns_false_for_file(self) -> None:
        with (
            patch.object(
                Path,
                "exists",
                return_value=True,
            ),
            patch.object(
                Path,
                "is_dir",
                return_value=False,
            ),
        ):
            result = directory_available("/file")

        self.assertFalse(result)

    def test_os_error_returns_false(self) -> None:
        with patch.object(
            Path,
            "exists",
            side_effect=OSError("permission denied"),
        ):
            result = directory_available("/restricted")

        self.assertFalse(result)

    def test_invalid_path_raises_before_filesystem(
        self,
    ) -> None:
        with (
            patch.object(Path, "exists") as exists,
            self.assertRaisesRegex(
                TypeError,
                ("path must be a string or Path"),
            ),
        ):
            directory_available(
                True  # type: ignore[arg-type]
            )

        exists.assert_not_called()


class OperatingSystemNameTests(unittest.TestCase):
    def test_combines_system_and_release(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.platform.system",
                return_value=" Linux ",
            ),
            patch(
                f"{MODULE}.platform.release",
                return_value=" 6.12 ",
            ),
        ):
            result = operating_system_name()

        self.assertEqual(
            result,
            "Linux 6.12",
        )

    def test_returns_system_without_release(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.platform.system",
                return_value="Linux",
            ),
            patch(
                f"{MODULE}.platform.release",
                return_value=" ",
            ),
        ):
            result = operating_system_name()

        self.assertEqual(
            result,
            "Linux",
        )

    def test_returns_unknown_when_empty(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.platform.system",
                return_value="",
            ),
            patch(
                f"{MODULE}.platform.release",
                return_value="",
            ),
        ):
            result = operating_system_name()

        self.assertEqual(
            result,
            "Unknown",
        )


class CollectPlatformInformationTests(unittest.TestCase):
    def test_collects_complete_report(
        self,
    ) -> None:
        summary = make_summary(
            ip_addresses=[
                "192.168.1.25",
                "192.168.1.25",
                "127.0.0.1",
                "0.0.0.0",
                "fe80::1",
                "",
            ]
        )
        storage = make_storage_information()
        media_results = (
            True,
            False,
            True,
        )

        with (
            patch(
                f"{MODULE}.collect_platform_summary",
                return_value=summary,
            ) as collect_summary,
            patch(
                f"{MODULE}.platform.python_version",
                return_value="3.11.2",
            ),
            patch(
                f"{MODULE}.operating_system_name",
                return_value="Linux 6.12",
            ),
            patch(
                f"{MODULE}.platform.machine",
                return_value=" aarch64 ",
            ),
            patch(
                f"{MODULE}.collect_storage_information",
                return_value=storage,
            ) as collect_storage,
            patch(
                f"{MODULE}.directory_available",
                side_effect=media_results,
            ) as available,
        ):
            result = collect_platform_information()

        collect_summary.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_storage.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG.health.disk_path
        )
        self.assertEqual(
            available.call_args_list,
            [
                call(DEFAULT_PLATFORM_CONFIG.paths.pictures_dir),
                call(DEFAULT_PLATFORM_CONFIG.paths.videos_dir),
                call(DEFAULT_PLATFORM_CONFIG.paths.sounds_dir),
            ],
        )

        self.assertEqual(
            result.robot.model,
            "Betabox Car",
        )
        self.assertEqual(
            result.robot.hostname,
            "Betabox-7eea",
        )
        self.assertEqual(
            result.robot.identifier,
            "7eea",
        )
        self.assertTrue(result.robot.control_available)

        self.assertEqual(
            result.network.ip_addresses,
            ("192.168.1.25",),
        )
        self.assertEqual(
            result.software.betabox_robotics_version,
            __version__,
        )
        self.assertEqual(
            result.software.architecture,
            "aarch64",
        )
        self.assertIs(
            result.storage,
            storage,
        )
        self.assertTrue(result.media.pictures_available)
        self.assertFalse(result.media.videos_available)
        self.assertTrue(result.media.sounds_available)
        self.assertTrue(result.features.vision_service_available)
        self.assertTrue(result.features.camera_ready)
        self.assertTrue(result.features.jupyterhub_available)

    def test_camera_not_ready_when_any_condition_fails(
        self,
    ) -> None:
        conditions = (
            {
                "vision_service_available": False,
            },
            {
                "vision_camera_running": False,
            },
            {
                "vision_camera_has_frame": False,
            },
        )

        for changes in conditions:
            with self.subTest(changes=changes):
                summary = make_summary(**changes)

                with (
                    patch(
                        f"{MODULE}.collect_platform_summary",
                        return_value=summary,
                    ),
                    patch(
                        f"{MODULE}.collect_storage_information",
                        return_value=make_storage_information(),
                    ),
                    patch(
                        f"{MODULE}.directory_available",
                        return_value=True,
                    ),
                ):
                    result = collect_platform_information()

                self.assertFalse(result.features.camera_ready)

    def test_unknown_hostname_prefix_has_no_identifier(
        self,
    ) -> None:
        summary = make_summary(hostname="Robot-7eea")

        with (
            patch(
                f"{MODULE}.collect_platform_summary",
                return_value=summary,
            ),
            patch(
                f"{MODULE}.collect_storage_information",
                return_value=make_storage_information(),
            ),
            patch(
                f"{MODULE}.directory_available",
                return_value=True,
            ),
        ):
            result = collect_platform_information()

        self.assertIsNone(result.robot.identifier)

    def test_unknown_architecture_uses_fallback(
        self,
    ) -> None:
        summary = make_summary()

        with (
            patch(
                f"{MODULE}.collect_platform_summary",
                return_value=summary,
            ),
            patch(
                f"{MODULE}.platform.machine",
                return_value=" ",
            ),
            patch(
                f"{MODULE}.collect_storage_information",
                return_value=make_storage_information(),
            ),
            patch(
                f"{MODULE}.directory_available",
                return_value=True,
            ),
        ):
            result = collect_platform_information()

        self.assertEqual(
            result.software.architecture,
            "Unknown",
        )

    def test_rejects_invalid_config_before_collection(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.collect_platform_summary") as collect_summary,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            collect_platform_information(
                object()  # type: ignore[arg-type]
            )

        collect_summary.assert_not_called()

    def test_empty_summary_hostname_raises(
        self,
    ) -> None:
        summary = make_summary(hostname=" ")

        with (
            patch(
                f"{MODULE}.collect_platform_summary",
                return_value=summary,
            ),
            self.assertRaisesRegex(
                ValueError,
                "hostname cannot be empty",
            ),
        ):
            collect_platform_information()

    def test_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("summary failed")

        with (
            patch(
                f"{MODULE}.collect_platform_summary",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_platform_information()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
