from __future__ import annotations

import argparse
import json
import subprocess
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    ServiceCategory,
    ServiceStartup,
)
from betabox_robotics.services.managed import (
    managed_services,
)
from betabox_robotics.services.services import (
    ServiceHealth,
    ServiceState,
    ServiceStatus,
    _validate_config,
    _validate_properties,
    _validate_statuses,
    _validate_string,
    collect_service,
    collect_services,
    format_service_state,
    main,
    normalize_state,
    parse_args,
    print_human,
    print_json,
    service_is_installed,
    service_properties,
    service_summary,
)

MODULE = "betabox_robotics.services.services"

MANAGED_SERVICES = managed_services(DEFAULT_PLATFORM_CONFIG)
DEFAULT_MANAGED = next(iter(MANAGED_SERVICES.values()))
DEFAULT_DEFINITION = DEFAULT_PLATFORM_CONFIG.services.get(DEFAULT_MANAGED.unit)

if DEFAULT_DEFINITION is None:
    raise RuntimeError("default managed service is missing from the service registry")


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


def make_status(
    *,
    name: str = "launchpad",
    display_name: str = "Launchpad",
    description: str = "Betabox Launchpad",
    unit: str = "betabox-launchpad.service",
    category: ServiceCategory = (DEFAULT_DEFINITION.category),
    startup: ServiceStartup = (ServiceStartup.CONTINUOUS),
    installed: bool = True,
    load_state: str = "loaded",
    active_state: str = "active",
    sub_state: str = "running",
    enabled_state: str = "enabled",
    state: ServiceState = ServiceState.RUNNING,
    health: ServiceHealth = ServiceHealth.HEALTHY,
) -> ServiceStatus:
    return ServiceStatus(
        name=name,
        display_name=display_name,
        description=description,
        unit=unit,
        category=category,
        startup=startup,
        installed=installed,
        load_state=load_state,
        active_state=active_state,
        sub_state=sub_state,
        enabled_state=enabled_state,
        state=state,
        health=health,
    )


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_platform_config(
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
                " service.service ",
                name="unit",
            ),
            "service.service",
        )

    def test_validate_string_allows_empty_when_requested(
        self,
    ) -> None:
        self.assertEqual(
            _validate_string(
                " ",
                name="result_state",
                allow_empty=True,
            ),
            "",
        )

    def test_validate_string_rejects_invalid_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "unit must be a string",
        ):
            _validate_string(
                None,
                name="unit",
            )

    def test_validate_string_rejects_empty_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unit cannot be empty",
        ):
            _validate_string(
                " ",
                name="unit",
            )

    def test_validate_properties_normalizes_values(
        self,
    ) -> None:
        result = _validate_properties(
            {
                " LoadState ": " loaded ",
                "ActiveState": " active ",
            }
        )

        self.assertEqual(
            result,
            {
                "LoadState": "loaded",
                "ActiveState": "active",
            },
        )

    def test_validate_properties_returns_copy(
        self,
    ) -> None:
        properties = {
            "LoadState": "loaded",
        }

        result = _validate_properties(properties)

        self.assertEqual(
            result,
            properties,
        )
        self.assertIsNot(
            result,
            properties,
        )

    def test_validate_properties_rejects_non_dict(
        self,
    ) -> None:
        for value in (
            None,
            [],
            (),
            "properties",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    ("properties must be a dictionary"),
                ),
            ):
                _validate_properties(value)

    def test_validate_properties_rejects_invalid_key(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("property name must be a string"),
        ):
            _validate_properties(
                {
                    1: "loaded",  # type: ignore[dict-item]
                }
            )

    def test_validate_properties_rejects_empty_key(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("property name cannot be empty"),
        ):
            _validate_properties(
                {
                    " ": "loaded",
                }
            )

    def test_validate_properties_rejects_invalid_value(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("property values must be strings"),
        ):
            _validate_properties(
                {
                    "LoadState": 1,  # type: ignore[dict-item]
                }
            )

    def test_validate_statuses_accepts_tuple(
        self,
    ) -> None:
        statuses = (make_status(),)

        result = _validate_statuses(statuses)

        self.assertIs(
            result,
            statuses,
        )

    def test_validate_statuses_accepts_empty_tuple(
        self,
    ) -> None:
        statuses: tuple[
            ServiceStatus,
            ...,
        ] = ()

        self.assertIs(
            _validate_statuses(statuses),
            statuses,
        )

    def test_validate_statuses_rejects_non_tuple(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "statuses must be a tuple",
        ):
            _validate_statuses(
                []  # type: ignore[arg-type]
            )

    def test_validate_statuses_rejects_invalid_item(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("statuses must contain only ServiceStatus values"),
        ):
            _validate_statuses(
                (
                    object(),  # type: ignore[arg-type]
                )
            )


class ServiceStatusTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        status = make_status()

        self.assertEqual(
            status.name,
            "launchpad",
        )
        self.assertEqual(
            status.state,
            ServiceState.RUNNING,
        )
        self.assertEqual(
            status.health,
            ServiceHealth.HEALTHY,
        )

    def test_strips_string_fields(self) -> None:
        status = make_status(
            name=" launchpad ",
            display_name=" Launchpad ",
            description=" Description ",
            unit=" service.service ",
            load_state=" loaded ",
            active_state=" active ",
            sub_state=" running ",
            enabled_state=" enabled ",
        )

        self.assertEqual(
            status.name,
            "launchpad",
        )
        self.assertEqual(
            status.display_name,
            "Launchpad",
        )
        self.assertEqual(
            status.description,
            "Description",
        )
        self.assertEqual(
            status.unit,
            "service.service",
        )
        self.assertEqual(
            status.load_state,
            "loaded",
        )

    def test_allows_empty_description(self) -> None:
        status = make_status(description=" ")

        self.assertEqual(
            status.description,
            "",
        )

    def test_rejects_invalid_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "name must be a string",
        ):
            make_status(
                name=None,  # type: ignore[arg-type]
            )

    def test_rejects_empty_name(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "name cannot be empty",
        ):
            make_status(name=" ")

    def test_rejects_invalid_category(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("category must be a ServiceCategory"),
        ):
            make_status(
                category="system",  # type: ignore[arg-type]
            )

    def test_rejects_invalid_startup(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("startup must be a ServiceStartup"),
        ):
            make_status(
                startup="continuous",  # type: ignore[arg-type]
            )

    def test_rejects_non_boolean_installed(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("installed must be a boolean"),
        ):
            make_status(
                installed=1,  # type: ignore[arg-type]
            )

    def test_rejects_empty_systemd_state(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("load_state cannot be empty"),
        ):
            make_status(load_state=" ")

    def test_rejects_invalid_state_enum(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("state must be a ServiceState"),
        ):
            make_status(
                state="running",  # type: ignore[arg-type]
            )

    def test_rejects_invalid_health_enum(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("health must be a ServiceHealth"),
        ):
            make_status(
                health="healthy",  # type: ignore[arg-type]
            )

    def test_to_dict_uses_enum_values(self) -> None:
        status = make_status()

        result = status.to_dict()

        self.assertEqual(
            result["category"],
            status.category.value,
        )
        self.assertEqual(
            result["startup"],
            "continuous",
        )
        self.assertEqual(
            result["state"],
            "running",
        )
        self.assertEqual(
            result["health"],
            "healthy",
        )

    def test_is_frozen(self) -> None:
        status = make_status()

        with self.assertRaises(FrozenInstanceError):
            status.installed = False  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        status = make_status()

        self.assertFalse(hasattr(status, "__dict__"))


class ServicePropertiesTests(unittest.TestCase):
    def test_runs_systemctl_show(self) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("LoadState=loaded\nActiveState=active\n"),
            ),
        ) as run:
            result = service_properties(" service.service ")

        run.assert_called_once_with(
            [
                "systemctl",
                "show",
                "service.service",
                "--no-pager",
                "--property=LoadState",
                "--property=ActiveState",
                "--property=SubState",
                "--property=UnitFileState",
                "--property=Result",
            ],
            timeout=5,
        )
        self.assertEqual(
            result,
            {
                "LoadState": "loaded",
                "ActiveState": "active",
            },
        )

    def test_parses_values_containing_equals(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout="Result=value=extra\n",
            ),
        ):
            result = service_properties("service.service")

        self.assertEqual(
            result,
            {
                "Result": "value=extra",
            },
        )

    def test_ignores_line_without_separator(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("invalid line\nLoadState=loaded\n"),
            ),
        ):
            result = service_properties("service.service")

        self.assertEqual(
            result,
            {
                "LoadState": "loaded",
            },
        )

    def test_ignores_empty_property_name(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                stdout=("=value\nLoadState=loaded\n"),
            ),
        ):
            result = service_properties("service.service")

        self.assertEqual(
            result,
            {
                "LoadState": "loaded",
            },
        )

    def test_returns_empty_when_command_fails_to_run(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=None,
        ):
            result = service_properties("service.service")

        self.assertEqual(result, {})

    def test_preserves_output_for_nonzero_result(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.run",
            return_value=make_result(
                returncode=1,
                stdout="LoadState=not-found\n",
            ),
        ):
            result = service_properties("missing.service")

        self.assertEqual(
            result,
            {
                "LoadState": "not-found",
            },
        )

    def test_rejects_invalid_unit_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                TypeError,
                "unit must be a string",
            ),
        ):
            service_properties(
                None  # type: ignore[arg-type]
            )

        run.assert_not_called()

    def test_rejects_empty_unit_before_command(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.run") as run,
            self.assertRaisesRegex(
                ValueError,
                "unit cannot be empty",
            ),
        ):
            service_properties(" ")

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
            service_properties("service.service")

        self.assertIs(
            context.exception,
            error,
        )


class ServiceIsInstalledTests(unittest.TestCase):
    def test_loaded_is_installed(self) -> None:
        self.assertTrue(
            service_is_installed(
                {
                    "LoadState": "loaded",
                }
            )
        )

    def test_other_load_state_is_not_installed(
        self,
    ) -> None:
        for value in (
            "not-found",
            "masked",
            "error",
            "",
        ):
            with self.subTest(value=value):
                self.assertFalse(
                    service_is_installed(
                        {
                            "LoadState": value,
                        }
                    )
                )

    def test_missing_load_state_is_not_installed(
        self,
    ) -> None:
        self.assertFalse(service_is_installed({}))

    def test_normalizes_load_state_key_and_value(
        self,
    ) -> None:
        self.assertTrue(
            service_is_installed(
                {
                    " LoadState ": " loaded ",
                }
            )
        )

    def test_rejects_invalid_properties(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("properties must be a dictionary"),
        ):
            service_is_installed(
                []  # type: ignore[arg-type]
            )


class NormalizeStateTests(unittest.TestCase):
    def normalize(
        self,
        *,
        installed: bool = True,
        active_state: str = "active",
        sub_state: str = "running",
        result_state: str = "success",
        startup: ServiceStartup = (ServiceStartup.CONTINUOUS),
    ) -> tuple[
        ServiceState,
        ServiceHealth,
    ]:
        return normalize_state(
            installed=installed,
            active_state=active_state,
            sub_state=sub_state,
            result_state=result_state,
            startup=startup,
        )

    def test_not_installed(self) -> None:
        self.assertEqual(
            self.normalize(installed=False),
            (
                ServiceState.NOT_INSTALLED,
                ServiceHealth.ERROR,
            ),
        )

    def test_failed_active_state(self) -> None:
        self.assertEqual(
            self.normalize(active_state="failed"),
            (
                ServiceState.FAILED,
                ServiceHealth.ERROR,
            ),
        )

    def test_failed_sub_state(self) -> None:
        self.assertEqual(
            self.normalize(sub_state="failed"),
            (
                ServiceState.FAILED,
                ServiceHealth.ERROR,
            ),
        )

    def test_failed_result_state(self) -> None:
        self.assertEqual(
            self.normalize(result_state="exit-code"),
            (
                ServiceState.FAILED,
                ServiceHealth.ERROR,
            ),
        )

    def test_allowed_result_states(self) -> None:
        for result_state in (
            "",
            "success",
            "done",
        ):
            with self.subTest(result_state=result_state):
                self.assertEqual(
                    self.normalize(result_state=result_state),
                    (
                        ServiceState.RUNNING,
                        ServiceHealth.HEALTHY,
                    ),
                )

    def test_activating(self) -> None:
        self.assertEqual(
            self.normalize(
                active_state="activating",
                sub_state="start",
            ),
            (
                ServiceState.STARTING,
                ServiceHealth.WARNING,
            ),
        )

    def test_deactivating(self) -> None:
        self.assertEqual(
            self.normalize(
                active_state="deactivating",
                sub_state="stop",
            ),
            (
                ServiceState.STOPPING,
                ServiceHealth.WARNING,
            ),
        )

    def test_reloading(self) -> None:
        self.assertEqual(
            self.normalize(
                active_state="reloading",
                sub_state="reload",
            ),
            (
                ServiceState.RELOADING,
                ServiceHealth.WARNING,
            ),
        )

    def test_active_running(self) -> None:
        self.assertEqual(
            self.normalize(),
            (
                ServiceState.RUNNING,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_active_exited_oneshot(self) -> None:
        self.assertEqual(
            self.normalize(
                sub_state="exited",
                startup=ServiceStartup.ONESHOT,
            ),
            (
                ServiceState.COMPLETED,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_active_exited_conditional(
        self,
    ) -> None:
        self.assertEqual(
            self.normalize(
                sub_state="exited",
                startup=(ServiceStartup.CONDITIONAL),
            ),
            (
                ServiceState.COMPLETED,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_active_exited_continuous_is_error(
        self,
    ) -> None:
        self.assertEqual(
            self.normalize(
                sub_state="exited",
            ),
            (
                ServiceState.INACTIVE,
                ServiceHealth.ERROR,
            ),
        )

    def test_active_unknown_substate_continuous(
        self,
    ) -> None:
        self.assertEqual(
            self.normalize(
                sub_state="listening",
            ),
            (
                ServiceState.RUNNING,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_active_unknown_substate_oneshot(
        self,
    ) -> None:
        self.assertEqual(
            self.normalize(
                sub_state="listening",
                startup=ServiceStartup.ONESHOT,
            ),
            (
                ServiceState.COMPLETED,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_inactive_conditional_waits(
        self,
    ) -> None:
        self.assertEqual(
            self.normalize(
                active_state="inactive",
                sub_state="dead",
                startup=(ServiceStartup.CONDITIONAL),
            ),
            (
                ServiceState.WAITING,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_inactive_successful_oneshot_is_completed(
        self,
    ) -> None:
        self.assertEqual(
            self.normalize(
                active_state="inactive",
                sub_state="dead",
                startup=ServiceStartup.ONESHOT,
            ),
            (
                ServiceState.COMPLETED,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_inactive_continuous_is_error(
        self,
    ) -> None:
        self.assertEqual(
            self.normalize(
                active_state="inactive",
                sub_state="dead",
            ),
            (
                ServiceState.INACTIVE,
                ServiceHealth.ERROR,
            ),
        )

    def test_unknown_active_state(self) -> None:
        self.assertEqual(
            self.normalize(
                active_state="maintenance",
                sub_state="unknown",
            ),
            (
                ServiceState.UNKNOWN,
                ServiceHealth.UNKNOWN,
            ),
        )

    def test_strips_state_values(self) -> None:
        self.assertEqual(
            self.normalize(
                active_state=" active ",
                sub_state=" running ",
                result_state=" success ",
            ),
            (
                ServiceState.RUNNING,
                ServiceHealth.HEALTHY,
            ),
        )

    def test_rejects_invalid_installed(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("installed must be a boolean"),
        ):
            self.normalize(
                installed=1,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_active_state(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("active_state must be a string"),
        ):
            self.normalize(
                active_state=None,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_startup(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("startup must be a ServiceStartup"),
        ):
            self.normalize(
                startup="continuous",  # type: ignore[arg-type]
            )


class CollectServiceTests(unittest.TestCase):
    def test_collects_service_status(self) -> None:
        properties = {
            "LoadState": "loaded",
            "ActiveState": "active",
            "SubState": "running",
            "UnitFileState": "enabled",
            "Result": "success",
        }

        with patch(
            f"{MODULE}.service_properties",
            return_value=properties,
        ) as get_properties:
            result = collect_service(
                DEFAULT_MANAGED,
                DEFAULT_PLATFORM_CONFIG,
            )

        get_properties.assert_called_once_with(DEFAULT_DEFINITION.unit)
        self.assertEqual(
            result.name,
            DEFAULT_MANAGED.name,
        )
        self.assertEqual(
            result.display_name,
            DEFAULT_DEFINITION.display_name,
        )
        self.assertEqual(
            result.unit,
            DEFAULT_DEFINITION.unit,
        )
        self.assertTrue(result.installed)
        self.assertEqual(
            result.state,
            ServiceState.RUNNING,
        )
        self.assertEqual(
            result.health,
            ServiceHealth.HEALTHY,
        )

    def test_missing_service_properties_are_not_installed(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.service_properties",
            return_value={},
        ):
            result = collect_service(
                DEFAULT_MANAGED,
                DEFAULT_PLATFORM_CONFIG,
            )

        self.assertFalse(result.installed)
        self.assertEqual(
            result.load_state,
            "unknown",
        )
        self.assertEqual(
            result.active_state,
            "not-installed",
        )
        self.assertEqual(
            result.sub_state,
            "not-installed",
        )
        self.assertEqual(
            result.enabled_state,
            "not-installed",
        )
        self.assertEqual(
            result.state,
            ServiceState.NOT_INSTALLED,
        )

    def test_loaded_service_with_missing_states_uses_unknown(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.service_properties",
            return_value={
                "LoadState": "loaded",
            },
        ):
            result = collect_service(
                DEFAULT_MANAGED,
                DEFAULT_PLATFORM_CONFIG,
            )

        self.assertTrue(result.installed)
        self.assertEqual(
            result.active_state,
            "unknown",
        )
        self.assertEqual(
            result.sub_state,
            "unknown",
        )
        self.assertEqual(
            result.enabled_state,
            "unknown",
        )

    def test_rejects_invalid_managed_service(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.service_properties") as get_properties,
            self.assertRaisesRegex(
                TypeError,
                ("managed must be a ManagedService"),
            ),
        ):
            collect_service(
                object(),  # type: ignore[arg-type]
                DEFAULT_PLATFORM_CONFIG,
            )

        get_properties.assert_not_called()

    def test_rejects_invalid_config_before_collection(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.service_properties") as get_properties,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            collect_service(
                DEFAULT_MANAGED,
                object(),  # type: ignore[arg-type]
            )

        get_properties.assert_not_called()

    def test_service_property_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("property collection failed")

        with (
            patch(
                f"{MODULE}.service_properties",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_service(
                DEFAULT_MANAGED,
                DEFAULT_PLATFORM_CONFIG,
            )

        self.assertIs(
            context.exception,
            error,
        )


class CollectServicesTests(unittest.TestCase):
    def test_collects_all_managed_services_in_order(
        self,
    ) -> None:
        managed = managed_services(DEFAULT_PLATFORM_CONFIG)
        expected = tuple(
            make_status(
                name=service.name,
                unit=service.unit,
            )
            for service in managed.values()
        )

        with (
            patch(
                f"{MODULE}.managed_services",
                return_value=managed,
            ) as get_managed,
            patch(
                f"{MODULE}.collect_service",
                side_effect=expected,
            ) as collect,
        ):
            result = collect_services(DEFAULT_PLATFORM_CONFIG)

        self.assertEqual(
            result,
            expected,
        )
        self.assertIsInstance(
            result,
            tuple,
        )
        get_managed.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        self.assertEqual(
            collect.call_args_list,
            [
                call(
                    service,
                    DEFAULT_PLATFORM_CONFIG,
                )
                for service in managed.values()
            ],
        )

    def test_accepts_empty_managed_registry(
        self,
    ) -> None:
        with patch(
            f"{MODULE}.managed_services",
            return_value={},
        ):
            result = collect_services()

        self.assertEqual(result, ())

    def test_rejects_invalid_config_before_lookup(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.managed_services") as get_managed,
            self.assertRaisesRegex(
                TypeError,
                ("config must be a PlatformConfig"),
            ),
        ):
            collect_services(
                object()  # type: ignore[arg-type]
            )

        get_managed.assert_not_called()

    def test_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("service collection failed")

        with (
            patch(
                f"{MODULE}.managed_services",
                return_value={
                    DEFAULT_MANAGED.name: (DEFAULT_MANAGED),
                },
            ),
            patch(
                f"{MODULE}.collect_service",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            collect_services()

        self.assertIs(
            context.exception,
            error,
        )


class ServiceSummaryTests(unittest.TestCase):
    def test_counts_all_health_states(self) -> None:
        statuses = (
            make_status(
                name="healthy",
                health=ServiceHealth.HEALTHY,
            ),
            make_status(
                name="warning",
                state=ServiceState.STARTING,
                health=ServiceHealth.WARNING,
            ),
            make_status(
                name="error",
                state=ServiceState.FAILED,
                health=ServiceHealth.ERROR,
            ),
            make_status(
                name="unknown",
                state=ServiceState.UNKNOWN,
                health=ServiceHealth.UNKNOWN,
            ),
        )

        self.assertEqual(
            service_summary(statuses),
            {
                "total": 4,
                "healthy": 1,
                "warning": 1,
                "error": 1,
                "unknown": 1,
            },
        )

    def test_empty_summary(self) -> None:
        self.assertEqual(
            service_summary(()),
            {
                "total": 0,
                "healthy": 0,
                "warning": 0,
                "error": 0,
                "unknown": 0,
            },
        )

    def test_rejects_invalid_statuses(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "statuses must be a tuple",
        ):
            service_summary(
                []  # type: ignore[arg-type]
            )


class FormatServiceStateTests(unittest.TestCase):
    def test_formats_every_state(self) -> None:
        expected = {
            ServiceState.RUNNING: "running",
            ServiceState.COMPLETED: "completed",
            ServiceState.WAITING: "waiting",
            ServiceState.STARTING: "starting",
            ServiceState.STOPPING: "stopping",
            ServiceState.RELOADING: "reloading",
            ServiceState.INACTIVE: "inactive",
            ServiceState.FAILED: "failed",
            ServiceState.NOT_INSTALLED: ("not installed"),
            ServiceState.UNKNOWN: "unknown",
        }

        for state, label in expected.items():
            with self.subTest(state=state):
                self.assertEqual(
                    format_service_state(make_status(state=state)),
                    label,
                )

    def test_rejects_invalid_status(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("status must be a ServiceStatus"),
        ):
            format_service_state(
                object()  # type: ignore[arg-type]
            )


class PrintHumanTests(unittest.TestCase):
    def test_prints_summary_and_services(
        self,
    ) -> None:
        statuses = (
            make_status(),
            make_status(
                name="monitor",
                display_name="Monitor",
                unit="betabox-monitor.service",
                active_state="activating",
                sub_state="start",
                enabled_state="enabled",
                state=ServiceState.STARTING,
                health=ServiceHealth.WARNING,
            ),
        )

        with patch("builtins.print") as print_message:
            print_human(statuses)

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Services"),
                call("================"),
                call(),
                call("Healthy: 1  Warning: 1  Errors: 0  Unknown: 0"),
                call(),
                call(
                    f"{'Launchpad':18} "
                    f"{'betabox-launchpad.service':36} "
                    f"{'running':14} "
                    "enabled"
                ),
                call(
                    f"{'Monitor':18} "
                    f"{'betabox-monitor.service':36} "
                    f"{'starting':14} "
                    "enabled"
                ),
                call(),
            ],
        )

    def test_rejects_invalid_statuses_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "statuses must be a tuple",
            ),
        ):
            print_human(
                []  # type: ignore[arg-type]
            )

        print_message.assert_not_called()


class PrintJsonTests(unittest.TestCase):
    def test_prints_json_payload(self) -> None:
        statuses = (make_status(),)

        with patch("builtins.print") as print_message:
            print_json(statuses)

        print_message.assert_called_once()
        payload = json.loads(print_message.call_args.args[0])

        self.assertEqual(
            payload["summary"],
            {
                "total": 1,
                "healthy": 1,
                "warning": 0,
                "error": 0,
                "unknown": 0,
            },
        )
        self.assertEqual(
            payload["services"],
            [
                statuses[0].to_dict(),
            ],
        )

    def test_uses_indented_json(self) -> None:
        statuses = (make_status(),)

        with (
            patch(
                f"{MODULE}.json.dumps",
                return_value="payload",
            ) as dumps,
            patch("builtins.print") as print_message,
        ):
            print_json(statuses)

        dumps.assert_called_once_with(
            {
                "summary": (service_summary(statuses)),
                "services": [
                    statuses[0].to_dict(),
                ],
            },
            indent=2,
        )
        print_message.assert_called_once_with("payload")

    def test_rejects_invalid_statuses_before_json(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.json.dumps") as dumps,
            self.assertRaisesRegex(
                TypeError,
                "statuses must be a tuple",
            ),
        ):
            print_json(
                []  # type: ignore[arg-type]
            )

        dumps.assert_not_called()


class ParseArgsTests(unittest.TestCase):
    def test_defaults_json_to_false(self) -> None:
        args = parse_args([])

        self.assertIsInstance(
            args,
            argparse.Namespace,
        )
        self.assertFalse(args.json)

    def test_parses_json_option(self) -> None:
        args = parse_args(
            [
                "--json",
            ]
        )

        self.assertTrue(args.json)

    def test_rejects_unknown_argument(self) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--unknown",
                ]
            )


class MainTests(unittest.TestCase):
    def test_prints_human_by_default(self) -> None:
        statuses = (make_status(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ) as parse_args_call,
            patch(
                f"{MODULE}.collect_services",
                return_value=statuses,
            ) as collect,
            patch(f"{MODULE}.print_human") as print_human_call,
            patch(f"{MODULE}.print_json") as print_json_call,
        ):
            result = main([])

        self.assertEqual(result, 0)
        parse_args_call.assert_called_once_with([])
        collect.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        print_human_call.assert_called_once_with(statuses)
        print_json_call.assert_not_called()

    def test_prints_json_when_requested(self) -> None:
        statuses = (make_status(),)

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=True),
            ),
            patch(
                f"{MODULE}.collect_services",
                return_value=statuses,
            ),
            patch(f"{MODULE}.print_human") as print_human_call,
            patch(f"{MODULE}.print_json") as print_json_call,
        ):
            result = main(
                [
                    "--json",
                ]
            )

        self.assertEqual(result, 0)
        print_json_call.assert_called_once_with(statuses)
        print_human_call.assert_not_called()

    def test_returns_one_for_type_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_services",
                side_effect=TypeError("invalid configuration"),
            ),
            patch(f"{MODULE}.print_human") as print_human_call,
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid configuration")
        print_human_call.assert_not_called()

    def test_returns_one_for_value_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_services",
                side_effect=ValueError("invalid registry"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid registry")

    def test_returns_one_for_os_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_services",
                side_effect=OSError("systemd unavailable"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("systemd unavailable")

    def test_unexpected_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_services",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )

    def test_output_error_propagates(self) -> None:
        statuses = (make_status(),)
        error = RuntimeError("printing failed")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(json=False),
            ),
            patch(
                f"{MODULE}.collect_services",
                return_value=statuses,
            ),
            patch(
                f"{MODULE}.print_human",
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
