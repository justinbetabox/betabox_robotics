from __future__ import annotations

import argparse
import json
import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from betabox_robotics.config import DEFAULT_PLATFORM_CONFIG
from betabox_robotics.services.doctor import (
    Diagnosis,
    DoctorReport,
    _validate_config,
    _validate_flag,
    _validate_non_negative_int,
    _validate_string,
    _validate_string_list,
    collect_diagnoses,
    collect_doctor_report,
    dedicated_service_units,
    diagnose_audio_hardware,
    diagnose_battery,
    diagnose_boot_announce,
    diagnose_grayscale,
    diagnose_guest_workspace,
    diagnose_jupyterhub,
    diagnose_launchpad,
    diagnose_media,
    diagnose_power,
    diagnose_robot_hardware,
    diagnose_services,
    diagnose_temperature,
    diagnose_vision_hardware,
    diagnosis_counts,
    healthy,
    main,
    print_diagnoses,
    result_map,
)
from betabox_robotics.services.guest import GuestWorkspaceStatus
from betabox_robotics.services.hardware_status import RobotHardwareStatus
from betabox_robotics.services.status import StatusReport
from betabox_robotics.services.system_health import SystemHealthStatus
from betabox_robotics.services.verify import CheckResult

MODULE = "betabox_robotics.services.doctor"


def make_diagnosis(
    *,
    title: str = "Example",
    ok: bool = True,
    severity: str = "info",
    summary: str = "Everything is working.",
    causes: tuple[str, ...] = (),
    affected: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> Diagnosis:
    return Diagnosis(
        title=title,
        ok=ok,
        severity=severity,  # type: ignore[arg-type]
        summary=summary,
        causes=causes,
        affected=affected,
        actions=actions,
    )


def make_issue(
    severity: str = "warning",
    *,
    title: str = "Issue",
) -> Diagnosis:
    return make_diagnosis(
        title=title,
        ok=False,
        severity=severity,
        summary="An issue was detected.",
        causes=("Cause",),
        affected=("Component",),
        actions=("Action",),
    )


def make_guest(
    *,
    account_exists: bool = True,
    home_exists: bool = True,
    curriculum_exists: bool = True,
    media_exists: bool = True,
    preferences_exist: bool = True,
) -> GuestWorkspaceStatus:
    return GuestWorkspaceStatus(
        account_exists=account_exists,
        home_exists=home_exists,
        curriculum_exists=curriculum_exists,
        media_exists=media_exists,
        preferences_exist=preferences_exist,
    )


def make_status(
    *,
    services: dict[str, str] | None = None,
    hardware: object | None = None,
    system_health: object | None = None,
    guest: GuestWorkspaceStatus | None = None,
) -> Mock:
    value = Mock(spec=StatusReport)
    value.services = services or {}
    value.hardware = hardware
    value.system_health = system_health
    value.guest = guest or make_guest()
    return value


def make_hardware(
    *,
    i2c_available: bool = True,
    passive_available: bool = True,
    passive_error: str | None = None,
    battery_available: bool = True,
    battery_voltage: float | None = 8.2,
    battery_state: str = "ok",
    battery_error: str | None = None,
    grayscale_available: bool = True,
    grayscale_values: list[int] | None = None,
    sensors_error: str | None = None,
    audio_available: bool = True,
    audio_device: str | None = "snd_rpi_hifiberry_dac",
    audio_error: str | None = None,
    vision_service_available: bool = True,
    vision_running: bool = True,
    camera_running: bool = True,
    camera_has_frame: bool = True,
    vision_error: str | None = None,
) -> Mock:
    value = Mock(spec=RobotHardwareStatus)
    value.i2c = SimpleNamespace(available=i2c_available)
    value.passive_hardware_available = passive_available
    value.passive_hardware_error = passive_error
    value.battery = SimpleNamespace(
        available=battery_available,
        voltage=battery_voltage,
        state=battery_state,
        error=battery_error,
    )
    value.sensors = SimpleNamespace(
        grayscale_available=grayscale_available,
        grayscale_values=(
            [100, 200, 300]
            if grayscale_values is None
            else grayscale_values
        ),
        error=sensors_error,
    )
    value.audio = SimpleNamespace(
        available=audio_available,
        device=audio_device,
        error=audio_error,
    )
    value.vision = SimpleNamespace(
        service_available=vision_service_available,
        running=vision_running,
        camera_running=camera_running,
        camera_has_frame=camera_has_frame,
        error=vision_error,
    )
    return value


def make_system_health(
    *,
    temperature: float | None = 45.0,
    temperature_state: str = "ok",
    temperature_error: str | None = None,
    undervoltage_now: bool = False,
    throttled_now: bool = False,
    undervoltage_occurred: bool = False,
    throttled_occurred: bool = False,
) -> Mock:
    value = Mock(spec=SystemHealthStatus)
    value.temperature = SimpleNamespace(
        celsius=temperature,
        state=temperature_state,
        error=temperature_error,
    )
    value.throttling = SimpleNamespace(
        undervoltage_now=undervoltage_now,
        throttled_now=throttled_now,
        undervoltage_occurred=undervoltage_occurred,
        throttled_occurred=throttled_occurred,
    )
    return value


def make_check(
    name: str,
    ok: bool,
    message: str = "",
) -> CheckResult:
    return CheckResult(name=name, ok=ok, message=message)


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_config(self) -> None:
        self.assertIs(
            _validate_config(DEFAULT_PLATFORM_CONFIG),
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_validate_config_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "config must be a PlatformConfig",
        ):
            _validate_config(object())

    def test_validate_string_strips_value(self) -> None:
        self.assertEqual(
            _validate_string(" value ", name="field"),
            "value",
        )

    def test_validate_string_rejects_invalid_type(self) -> None:
        with self.assertRaisesRegex(TypeError, "field must be a string"):
            _validate_string(1, name="field")

    def test_validate_string_rejects_empty_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "field cannot be empty"):
            _validate_string(" ", name="field")

    def test_validate_flag_accepts_boolean(self) -> None:
        self.assertTrue(_validate_flag(True, name="ok"))
        self.assertFalse(_validate_flag(False, name="ok"))

    def test_validate_flag_rejects_non_boolean(self) -> None:
        with self.assertRaisesRegex(TypeError, "ok must be a boolean"):
            _validate_flag(1, name="ok")

    def test_validate_non_negative_int_accepts_zero(self) -> None:
        self.assertEqual(
            _validate_non_negative_int(0, name="count"),
            0,
        )

    def test_validate_non_negative_int_rejects_boolean(self) -> None:
        with self.assertRaisesRegex(TypeError, "count must be an integer"):
            _validate_non_negative_int(True, name="count")

    def test_validate_non_negative_int_rejects_negative(self) -> None:
        with self.assertRaisesRegex(ValueError, "count cannot be negative"):
            _validate_non_negative_int(-1, name="count")

    def test_validate_string_list_normalizes_values(self) -> None:
        self.assertEqual(
            _validate_string_list([" one ", "two"], name="items"),
            ("one", "two"),
        )

    def test_validate_string_list_rejects_invalid_container(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "items must be a list or tuple",
        ):
            _validate_string_list("value", name="items")


class DiagnosisTests(unittest.TestCase):
    def test_normalizes_fields(self) -> None:
        value = make_diagnosis(
            title=" Example ",
            severity=" INFO ",
            summary=" Healthy ",
            causes=(" Cause ",),
            affected=(" Component ",),
            actions=(" Action ",),
        )

        self.assertEqual(value.title, "Example")
        self.assertEqual(value.severity, "info")
        self.assertEqual(value.summary, "Healthy")
        self.assertEqual(value.causes, ("Cause",))

    def test_accepts_all_severities(self) -> None:
        for severity in ("info", "warning", "error", "critical"):
            with self.subTest(severity=severity):
                value = make_diagnosis(
                    ok=(severity == "info"),
                    severity=severity,
                )
                self.assertEqual(value.severity, severity)

    def test_rejects_unknown_severity(self) -> None:
        with self.assertRaisesRegex(ValueError, "severity must be one of"):
            make_diagnosis(severity="debug")

    def test_rejects_non_info_healthy_diagnosis(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "healthy diagnoses must use info severity",
        ):
            make_diagnosis(ok=True, severity="warning")

    def test_rejects_empty_cause(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "causes item cannot be empty",
        ):
            make_diagnosis(causes=(" ",))

    def test_is_frozen_and_slotted(self) -> None:
        value = make_diagnosis()
        self.assertFalse(hasattr(value, "__dict__"))

        with self.assertRaises(FrozenInstanceError):
            value.title = "Changed"  # type: ignore[misc]


class DoctorReportTests(unittest.TestCase):
    def test_healthy_report_properties(self) -> None:
        diagnoses = (
            make_diagnosis(title="A"),
            make_diagnosis(title="B"),
        )
        report = DoctorReport(
            diagnoses=diagnoses,
            critical=0,
            error=0,
            warning=0,
            healthy=2,
        )

        self.assertEqual(report.total, 2)
        self.assertEqual(report.issues, 0)
        self.assertTrue(report.ok)
        self.assertEqual(report.overall, "healthy")

    def test_overall_uses_highest_severity(self) -> None:
        cases = (
            ((make_issue("warning"),), (0, 0, 1, 0), "warning"),
            ((make_issue("error"),), (0, 1, 0, 0), "error"),
            ((make_issue("critical"),), (1, 0, 0, 0), "critical"),
        )

        for diagnoses, counts, expected in cases:
            with self.subTest(expected=expected):
                report = DoctorReport(
                    diagnoses=diagnoses,
                    critical=counts[0],
                    error=counts[1],
                    warning=counts[2],
                    healthy=counts[3],
                )
                self.assertEqual(report.overall, expected)

    def test_rejects_non_tuple_diagnoses(self) -> None:
        with self.assertRaisesRegex(TypeError, "diagnoses must be a tuple"):
            DoctorReport(
                diagnoses=[],  # type: ignore[arg-type]
                critical=0,
                error=0,
                warning=0,
                healthy=0,
            )

    def test_rejects_invalid_diagnosis_item(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "diagnoses must contain only Diagnosis values",
        ):
            DoctorReport(
                diagnoses=(object(),),  # type: ignore[arg-type]
                critical=0,
                error=0,
                warning=0,
                healthy=0,
            )

    def test_rejects_mismatched_counts(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "diagnosis counts do not match diagnoses",
        ):
            DoctorReport(
                diagnoses=(make_diagnosis(),),
                critical=0,
                error=0,
                warning=0,
                healthy=0,
            )

    def test_to_dict_contains_summary_and_diagnoses(self) -> None:
        report = DoctorReport(
            diagnoses=(make_diagnosis(),),
            critical=0,
            error=0,
            warning=0,
            healthy=1,
        )
        result = report.to_dict()

        self.assertEqual(result["summary"]["overall"], "healthy")  # type: ignore[index]
        self.assertEqual(result["summary"]["total"], 1)  # type: ignore[index]
        self.assertEqual(len(result["diagnoses"]), 1)  # type: ignore[arg-type]


class HelperTests(unittest.TestCase):
    def test_dedicated_service_units(self) -> None:
        self.assertEqual(
            dedicated_service_units(),
            {
                DEFAULT_PLATFORM_CONFIG.services.video.unit,
                DEFAULT_PLATFORM_CONFIG.services.jupyterhub.unit,
                DEFAULT_PLATFORM_CONFIG.services.boot_announce.unit,
                DEFAULT_PLATFORM_CONFIG.services.launchpad.unit,
            },
        )

    def test_healthy_builds_info_diagnosis(self) -> None:
        result = healthy(" Healthy ", " Everything works. ")

        self.assertTrue(result.ok)
        self.assertEqual(result.severity, "info")
        self.assertEqual(result.title, "Healthy")
        self.assertEqual(result.causes, ())

    def test_result_map_builds_name_mapping(self) -> None:
        first = make_check("one", True)
        second = make_check("two", False)

        self.assertEqual(
            result_map([first, second]),
            {"one": first, "two": second},
        )

    def test_result_map_uses_last_duplicate(self) -> None:
        first = make_check("one", False)
        second = make_check("one", True)
        self.assertIs(result_map([first, second])["one"], second)

    def test_result_map_rejects_invalid_container(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "results must be a list or tuple",
        ):
            result_map("invalid")  # type: ignore[arg-type]

    def test_diagnosis_counts(self) -> None:
        diagnoses = (
            make_diagnosis(title="Healthy"),
            make_issue("warning", title="Warning"),
            make_issue("error", title="Error"),
            make_issue("critical", title="Critical"),
        )

        self.assertEqual(
            diagnosis_counts(diagnoses),
            {
                "critical": 1,
                "error": 1,
                "warning": 1,
                "healthy": 1,
            },
        )


class BootAnnounceDiagnosisTests(unittest.TestCase):
    def test_active_and_inactive_are_healthy(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.boot_announce.unit

        active = diagnose_boot_announce(
            make_status(services={unit: "active"})
        )
        inactive = diagnose_boot_announce(
            make_status(services={unit: "inactive"})
        )

        self.assertTrue(active.ok)
        self.assertTrue(inactive.ok)
        self.assertIn("running", active.summary)
        self.assertIn("completed successfully", inactive.summary)

    def test_failed_is_warning(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.boot_announce.unit
        result = diagnose_boot_announce(
            make_status(services={unit: "failed"})
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.severity, "warning")

    def test_unknown_state_is_warning(self) -> None:
        result = diagnose_boot_announce(make_status())

        self.assertEqual(result.severity, "warning")
        self.assertIn("unknown", result.summary)


class MediaDiagnosisTests(unittest.TestCase):
    def test_all_media_checks_are_healthy(self) -> None:
        results = {
            name: make_check(name, True)
            for name in (
                "media:pictures",
                "media:videos",
                "media:sounds",
            )
        }
        self.assertTrue(diagnose_media(results).ok)

    def test_missing_check_is_warning(self) -> None:
        result = diagnose_media(
            {"media:pictures": make_check("media:pictures", True)}
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.severity, "warning")


class GuestWorkspaceDiagnosisTests(unittest.TestCase):
    def test_ready_workspace_is_healthy(self) -> None:
        self.assertTrue(diagnose_guest_workspace(make_guest()).ok)

    def test_missing_workspace_reports_affected_sections(self) -> None:
        result = diagnose_guest_workspace(
            make_guest(
                account_exists=False,
                home_exists=False,
                curriculum_exists=False,
                media_exists=False,
                preferences_exist=False,
            )
        )

        self.assertEqual(result.severity, "error")
        self.assertIn("Guest account", result.affected)
        self.assertIn("Guest home", result.affected)
        self.assertIn("The Guest account is missing.", result.causes)

    def test_partial_workspace_reports_corruption(self) -> None:
        result = diagnose_guest_workspace(
            make_guest(media_exists=False)
        )

        self.assertIn(
            "Workspace files may have been removed or corrupted.",
            result.causes,
        )


class ManagedServicesDiagnosisTests(unittest.TestCase):
    def test_failed_non_dedicated_service_is_error(self) -> None:
        service = SimpleNamespace(
            title="Monitor",
            unit="betabox-monitor.service",
        )

        with patch(
            f"{MODULE}.managed_services",
            return_value={"monitor": service},
        ):
            result = diagnose_services(
                make_status(services={service.unit: "failed"})
            )

        self.assertEqual(result.severity, "error")
        self.assertEqual(result.affected, ("Monitor",))

    def test_non_ready_service_is_warning(self) -> None:
        service = SimpleNamespace(
            title="Monitor",
            unit="betabox-monitor.service",
        )

        with patch(
            f"{MODULE}.managed_services",
            return_value={"monitor": service},
        ):
            result = diagnose_services(
                make_status(services={service.unit: "activating"})
            )

        self.assertEqual(result.severity, "warning")
        self.assertEqual(result.affected, ("Monitor (activating)",))

    def test_ready_service_is_healthy(self) -> None:
        service = SimpleNamespace(
            title="Monitor",
            unit="betabox-monitor.service",
        )

        with patch(
            f"{MODULE}.managed_services",
            return_value={"monitor": service},
        ):
            result = diagnose_services(
                make_status(services={service.unit: "active"})
            )

        self.assertTrue(result.ok)


class JupyterHubDiagnosisTests(unittest.TestCase):
    def test_complete_jupyterhub_is_healthy(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.jupyterhub.unit
        results = {
            "jupyterhub:proxy": make_check("jupyterhub:proxy", True)
        }

        with patch(
            f"{MODULE}.check_http_available",
            return_value=(True, "ok"),
        ) as check:
            result = diagnose_jupyterhub(
                results,
                make_status(services={unit: "active"}),
            )

        self.assertTrue(result.ok)
        check.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG.network.jupyterhub_health_url
        )

    def test_missing_proxy_is_error(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.jupyterhub.unit

        with patch(
            f"{MODULE}.check_http_available",
            return_value=(True, "ok"),
        ):
            result = diagnose_jupyterhub(
                {},
                make_status(services={unit: "active"}),
            )

        self.assertEqual(result.severity, "error")
        self.assertIn(
            "configurable-http-proxy is missing or unavailable.",
            result.causes,
        )

    def test_inactive_service_skips_http_check(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.jupyterhub.unit
        results = {
            "jupyterhub:proxy": make_check("jupyterhub:proxy", True)
        }

        with patch(f"{MODULE}.check_http_available") as check:
            result = diagnose_jupyterhub(
                results,
                make_status(services={unit: "inactive"}),
            )

        self.assertEqual(result.severity, "error")
        check.assert_not_called()

    def test_failed_endpoint_is_reported(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.jupyterhub.unit
        results = {
            "jupyterhub:proxy": make_check("jupyterhub:proxy", True)
        }

        with patch(
            f"{MODULE}.check_http_available",
            return_value=(False, "connection refused"),
        ):
            result = diagnose_jupyterhub(
                results,
                make_status(services={unit: "active"}),
            )

        self.assertTrue(
            any("connection refused" in cause for cause in result.causes)
        )


class HardwareDiagnosisTests(unittest.TestCase):
    def test_robot_hardware_branches(self) -> None:
        missing_i2c = diagnose_robot_hardware(
            make_hardware(i2c_available=False)
        )
        missing_passive = diagnose_robot_hardware(
            make_hardware(
                passive_available=False,
                passive_error="construct failed",
            )
        )
        healthy_result = diagnose_robot_hardware(make_hardware())

        self.assertEqual(missing_i2c.severity, "critical")
        self.assertEqual(missing_passive.severity, "critical")
        self.assertEqual(missing_passive.summary, "construct failed")
        self.assertTrue(healthy_result.ok)

    def test_battery_branches(self) -> None:
        unavailable = diagnose_battery(
            make_hardware(
                battery_available=False,
                battery_voltage=None,
                battery_error="ADC unavailable",
            )
        )
        critical = diagnose_battery(
            make_hardware(
                battery_voltage=6.1,
                battery_state="critical",
            )
        )
        low = diagnose_battery(
            make_hardware(
                battery_voltage=6.5,
                battery_state="low",
            )
        )
        healthy_result = diagnose_battery(make_hardware())

        self.assertEqual(unavailable.severity, "error")
        self.assertEqual(critical.severity, "critical")
        self.assertEqual(low.severity, "warning")
        self.assertTrue(healthy_result.ok)

    def test_grayscale_branches(self) -> None:
        available = diagnose_grayscale(
            make_hardware(grayscale_values=[1, 2, 3])
        )
        unavailable = diagnose_grayscale(
            make_hardware(
                grayscale_available=False,
                sensors_error="sensor unavailable",
            )
        )

        self.assertTrue(available.ok)
        self.assertIn("1, 2, 3", available.summary)
        self.assertEqual(unavailable.severity, "warning")

    def test_audio_branches(self) -> None:
        available = diagnose_audio_hardware(
            make_hardware(audio_device="HifiBerry")
        )
        unavailable = diagnose_audio_hardware(
            make_hardware(
                audio_available=False,
                audio_error="device missing",
            )
        )

        self.assertTrue(available.ok)
        self.assertIn("HifiBerry", available.summary)
        self.assertEqual(unavailable.severity, "warning")

    def test_vision_branches(self) -> None:
        service = diagnose_vision_hardware(
            make_hardware(vision_service_available=False)
        )
        runtime = diagnose_vision_hardware(
            make_hardware(vision_running=False)
        )
        camera = diagnose_vision_hardware(
            make_hardware(camera_running=False)
        )
        frame = diagnose_vision_hardware(
            make_hardware(camera_has_frame=False)
        )
        healthy_result = diagnose_vision_hardware(make_hardware())

        self.assertEqual(service.severity, "error")
        self.assertEqual(runtime.severity, "error")
        self.assertEqual(camera.severity, "error")
        self.assertEqual(frame.severity, "warning")
        self.assertTrue(healthy_result.ok)


class LaunchpadDiagnosisTests(unittest.TestCase):
    def test_inactive_service_is_error(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit
        result = diagnose_launchpad(
            make_status(services={unit: "inactive"})
        )

        self.assertEqual(result.severity, "error")
        self.assertIn("inactive", result.summary)

    def test_active_healthy_service_is_healthy(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with patch(
            f"{MODULE}.check_json_health",
            return_value=(True, "ok"),
        ) as check:
            result = diagnose_launchpad(
                make_status(services={unit: "active"})
            )

        self.assertTrue(result.ok)
        check.assert_called_once_with(
            DEFAULT_PLATFORM_CONFIG.network.launchpad_health_url,
            expected_service="launchpad",
        )

    def test_active_failed_health_is_error(self) -> None:
        unit = DEFAULT_PLATFORM_CONFIG.services.launchpad.unit

        with patch(
            f"{MODULE}.check_json_health",
            return_value=(False, "invalid response"),
        ):
            result = diagnose_launchpad(
                make_status(services={unit: "active"})
            )

        self.assertEqual(result.severity, "error")
        self.assertIn("invalid response", result.summary)


class SystemDiagnosisTests(unittest.TestCase):
    def test_temperature_branches(self) -> None:
        unavailable = diagnose_temperature(
            make_system_health(
                temperature=None,
                temperature_error="sensor missing",
            )
        )
        critical = diagnose_temperature(
            make_system_health(
                temperature=82.0,
                temperature_state="critical",
            )
        )
        high = diagnose_temperature(
            make_system_health(
                temperature=75.0,
                temperature_state="high",
            )
        )
        healthy_result = diagnose_temperature(make_system_health())

        self.assertEqual(unavailable.severity, "warning")
        self.assertEqual(
            unavailable.causes,
            ("Thermal sensor data could not be read.",),
        )
        self.assertEqual(critical.severity, "critical")
        self.assertEqual(high.severity, "warning")
        self.assertTrue(healthy_result.ok)

    def test_power_branches(self) -> None:
        undervoltage = diagnose_power(
            make_system_health(undervoltage_now=True)
        )
        throttled = diagnose_power(
            make_system_health(throttled_now=True)
        )
        historical = diagnose_power(
            make_system_health(undervoltage_occurred=True)
        )
        healthy_result = diagnose_power(make_system_health())

        self.assertEqual(undervoltage.severity, "critical")
        self.assertEqual(throttled.severity, "error")
        self.assertEqual(historical.severity, "warning")
        self.assertEqual(
            historical.affected,
            ("Historical system reliability",),
        )
        self.assertTrue(healthy_result.ok)


class CollectDiagnosesTests(unittest.TestCase):
    def test_collects_optional_sensor_checks_when_robot_is_healthy(self) -> None:
        hardware = make_hardware()
        status = make_status(
            hardware=hardware,
            system_health=make_system_health(),
        )

        with (
            patch(f"{MODULE}.collect_status", return_value=status),
            patch(f"{MODULE}.collect_checks", return_value=()),
            patch(
                f"{MODULE}.diagnose_robot_hardware",
                return_value=healthy("Robot Hardware", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_vision_hardware",
                return_value=healthy("Vision", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_temperature",
                return_value=healthy("Temperature", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_power",
                return_value=healthy("Power", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_guest_workspace",
                return_value=healthy("Guest", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_audio_hardware",
                return_value=healthy("Audio", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_jupyterhub",
                return_value=healthy("JupyterHub", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_launchpad",
                return_value=healthy("Launchpad", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_boot_announce",
                return_value=healthy("Boot", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_media",
                return_value=healthy("Media", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_services",
                return_value=healthy("Services", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_battery",
                return_value=healthy("Battery", "healthy"),
            ) as battery,
            patch(
                f"{MODULE}.diagnose_grayscale",
                return_value=healthy("Grayscale", "healthy"),
            ) as grayscale,
        ):
            result = collect_diagnoses()

        self.assertEqual(len(result), 13)
        battery.assert_called_once_with(hardware)
        grayscale.assert_called_once_with(hardware)

    def test_skips_optional_sensor_checks_when_robot_fails(self) -> None:
        hardware = make_hardware()
        status = make_status(
            hardware=hardware,
            system_health=make_system_health(),
        )

        with (
            patch(f"{MODULE}.collect_status", return_value=status),
            patch(f"{MODULE}.collect_checks", return_value=()),
            patch(
                f"{MODULE}.diagnose_robot_hardware",
                return_value=make_issue("critical", title="Robot Hardware"),
            ),
            patch(
                f"{MODULE}.diagnose_vision_hardware",
                return_value=healthy("Vision", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_temperature",
                return_value=healthy("Temperature", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_power",
                return_value=healthy("Power", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_guest_workspace",
                return_value=healthy("Guest", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_audio_hardware",
                return_value=healthy("Audio", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_jupyterhub",
                return_value=healthy("JupyterHub", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_launchpad",
                return_value=healthy("Launchpad", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_boot_announce",
                return_value=healthy("Boot", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_media",
                return_value=healthy("Media", "healthy"),
            ),
            patch(
                f"{MODULE}.diagnose_services",
                return_value=healthy("Services", "healthy"),
            ),
            patch(f"{MODULE}.diagnose_battery") as battery,
            patch(f"{MODULE}.diagnose_grayscale") as grayscale,
        ):
            result = collect_diagnoses()

        self.assertEqual(len(result), 11)
        battery.assert_not_called()
        grayscale.assert_not_called()


class CollectDoctorReportTests(unittest.TestCase):
    def test_sorts_and_counts_diagnoses(self) -> None:
        diagnoses = (
            make_diagnosis(title="Healthy Z"),
            make_issue("warning", title="Warning B"),
            make_issue("critical", title="Critical A"),
            make_issue("error", title="Error C"),
            make_diagnosis(title="Healthy A"),
        )

        with patch(
            f"{MODULE}.collect_diagnoses",
            return_value=diagnoses,
        ):
            report = collect_doctor_report()

        self.assertEqual(
            tuple(item.title for item in report.diagnoses),
            (
                "Critical A",
                "Error C",
                "Warning B",
                "Healthy A",
                "Healthy Z",
            ),
        )
        self.assertEqual(report.critical, 1)
        self.assertEqual(report.error, 1)
        self.assertEqual(report.warning, 1)
        self.assertEqual(report.healthy, 2)


class PrintDiagnosesTests(unittest.TestCase):
    def test_prints_healthy_report(self) -> None:
        diagnoses = (
            make_diagnosis(title="Healthy", summary="Everything works."),
        )

        with patch("builtins.print") as print_message:
            result = print_diagnoses(diagnoses)

        self.assertTrue(result)
        self.assertIn(call("[OK] Healthy"), print_message.call_args_list)
        self.assertIn(
            call("No major platform issues detected."),
            print_message.call_args_list,
        )

    def test_prints_issue_details(self) -> None:
        diagnoses = (make_issue("error", title="Broken"),)

        with patch("builtins.print") as print_message:
            result = print_diagnoses(diagnoses)

        self.assertFalse(result)
        self.assertIn(call("[ERROR] Broken"), print_message.call_args_list)
        self.assertIn(call("      - Cause"), print_message.call_args_list)
        self.assertIn(call("      1. Action"), print_message.call_args_list)
        self.assertIn(
            call("One or more issues were detected."),
            print_message.call_args_list,
        )


class MainTests(unittest.TestCase):
    def test_prints_human_healthy_report(self) -> None:
        report = DoctorReport(
            diagnoses=(make_diagnosis(),),
            critical=0,
            error=0,
            warning=0,
            healthy=1,
        )

        with (
            patch.object(
                argparse.ArgumentParser,
                "parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_doctor_report",
                return_value=report,
            ),
            patch(f"{MODULE}.print_diagnoses") as print_call,
        ):
            result = main([])

        self.assertEqual(result, 0)
        print_call.assert_called_once_with(report.diagnoses)

    def test_prints_human_unhealthy_report(self) -> None:
        report = DoctorReport(
            diagnoses=(make_issue("error"),),
            critical=0,
            error=1,
            warning=0,
            healthy=0,
        )

        with (
            patch.object(
                argparse.ArgumentParser,
                "parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_doctor_report",
                return_value=report,
            ),
            patch(f"{MODULE}.print_diagnoses"),
        ):
            result = main([])

        self.assertEqual(result, 1)

    def test_prints_json_report(self) -> None:
        report = DoctorReport(
            diagnoses=(make_diagnosis(),),
            critical=0,
            error=0,
            warning=0,
            healthy=1,
        )

        with (
            patch.object(
                argparse.ArgumentParser,
                "parse_args",
                return_value=argparse.Namespace(json=True),
            ),
            patch(
                f"{MODULE}.collect_doctor_report",
                return_value=report,
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(["--json"])

        self.assertEqual(result, 0)
        print_message.assert_called_once_with(
            json.dumps(report.to_dict(), indent=2)
        )


if __name__ == "__main__":
    unittest.main()
