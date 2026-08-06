from __future__ import annotations

import argparse
import json
import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import Mock, call, mock_open, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.monitor import (
    MonitorEvent,
    _build_parser,
    _validate_config,
    _validate_interval,
    _validate_mapping,
    _validate_string,
    collect_snapshot,
    find_changes,
    log,
    main,
    message_for_change,
    parse_args,
    run_forever,
    run_once,
    severity_for_change,
    summarize,
    timestamp,
    write_event,
)

MODULE = "betabox_robotics.services.monitor"


def make_event(
    *,
    timestamp_value: str = "2026-08-05 18:00:00",
    severity: str = "warning",
    component: str = "system",
    event: str = "system.disk_state",
    previous: object = "ok",
    current: object = "high",
    message: str = "Disk usage changed from 'ok' to 'high'",
) -> MonitorEvent:
    return MonitorEvent(
        timestamp=timestamp_value,
        severity=severity,  # type: ignore[arg-type]
        component=component,
        event=event,
        previous=previous,
        current=current,
        message=message,
    )


def make_snapshot() -> dict[str, object]:
    return {
        "services": {
            "launchpad.service": "active",
            "jupyterhub.service": "active",
        },
        "hardware": {
            "passive_hardware_available": True,
            "i2c": {
                "available": True,
                "devices": [
                    "0x14",
                    "0x40",
                ],
            },
            "battery": {
                "state": "ok",
            },
            "sensors": {
                "grayscale_available": True,
            },
            "audio": {
                "available": True,
            },
            "vision": {
                "service_available": True,
                "running": True,
                "camera_running": True,
                "camera_has_frame": True,
            },
        },
        "system_health": {
            "temperature": {
                "state": "ok",
            },
            "throttling": {
                "undervoltage_now": False,
                "undervoltage_occurred": False,
                "throttled_now": False,
                "throttled_occurred": False,
            },
            "memory": {
                "state": "ok",
            },
            "disk": {
                "state": "ok",
            },
            "ethernet": {
                "connected": True,
            },
            "wifi": {
                "connected": True,
            },
        },
    }


def make_summary() -> dict[str, object]:
    return {
        "services": {
            "launchpad.service": "active",
            "jupyterhub.service": "active",
        },
        "hardware": {
            "robot_available": True,
            "i2c_available": True,
            "i2c_devices": [
                "0x14",
                "0x40",
            ],
            "battery_state": "ok",
            "grayscale_available": True,
            "audio_available": True,
            "vision_service_available": True,
            "vision_running": True,
            "camera_running": True,
            "camera_has_frame": True,
        },
        "system": {
            "temperature_state": "ok",
            "undervoltage_now": False,
            "undervoltage_occurred": False,
            "throttled_now": False,
            "throttled_occurred": False,
            "memory_state": "ok",
            "disk_state": "ok",
            "ethernet_connected": True,
            "wifi_connected": True,
        },
    }


class ValidationTests(unittest.TestCase):
    def test_validate_config_accepts_config(self) -> None:
        result = _validate_config(DEFAULT_PLATFORM_CONFIG)

        self.assertIs(
            result,
            DEFAULT_PLATFORM_CONFIG,
        )

    def test_validate_config_rejects_invalid_value(self) -> None:
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
                    "config must be a PlatformConfig",
                ),
            ):
                _validate_config(value)

    def test_validate_string_strips_value(self) -> None:
        result = _validate_string(
            " monitor started ",
            name="message",
        )

        self.assertEqual(
            result,
            "monitor started",
        )

    def test_validate_string_rejects_invalid_type(self) -> None:
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
                    "message must be a string",
                ),
            ):
                _validate_string(
                    value,
                    name="message",
                )

    def test_validate_string_rejects_empty_value(self) -> None:
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
                    "message cannot be empty",
                ),
            ):
                _validate_string(
                    value,
                    name="message",
                )

    def test_validate_interval_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_interval(30),
            30,
        )

    def test_validate_interval_rejects_boolean(self) -> None:
        for value in (
            True,
            False,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "interval_seconds must be an integer",
                ),
            ):
                _validate_interval(value)

    def test_validate_interval_rejects_invalid_type(self) -> None:
        for value in (
            None,
            1.5,
            "30",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "interval_seconds must be an integer",
                ),
            ):
                _validate_interval(value)

    def test_validate_interval_rejects_non_positive(self) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "interval_seconds must be greater than 0",
                ),
            ):
                _validate_interval(value)

    def test_validate_mapping_accepts_dictionary(self) -> None:
        value = {
            "status": "ok",
        }

        result = _validate_mapping(
            value,
            name="snapshot",
        )

        self.assertIs(
            result,
            value,
        )

    def test_validate_mapping_rejects_invalid_value(self) -> None:
        for value in (
            None,
            [],
            (),
            "mapping",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "snapshot must be a dictionary",
                ),
            ):
                _validate_mapping(
                    value,
                    name="snapshot",
                )


class MonitorEventTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        event = make_event()

        self.assertEqual(
            event.severity,
            "warning",
        )
        self.assertEqual(
            event.component,
            "system",
        )

    def test_strips_string_values(self) -> None:
        event = make_event(
            timestamp_value=" 2026-08-05 18:00:00 ",
            severity=" WARNING ",
            component=" system ",
            event=" system.disk_state ",
            message=" Disk usage high ",
        )

        self.assertEqual(
            event.timestamp,
            "2026-08-05 18:00:00",
        )
        self.assertEqual(
            event.severity,
            "warning",
        )
        self.assertEqual(
            event.component,
            "system",
        )
        self.assertEqual(
            event.event,
            "system.disk_state",
        )
        self.assertEqual(
            event.message,
            "Disk usage high",
        )

    def test_accepts_each_severity(self) -> None:
        for severity in (
            "info",
            "warning",
            "error",
            "critical",
        ):
            with self.subTest(severity=severity):
                self.assertEqual(
                    make_event(severity=severity).severity,
                    severity,
                )

    def test_rejects_invalid_severity_type(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "severity must be a string",
        ):
            make_event(
                severity=1  # type: ignore[arg-type]
            )

    def test_rejects_unknown_severity(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("severity must be one of: critical, error, info, warning"),
        ):
            make_event(severity="debug")

    def test_rejects_empty_component(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "component cannot be empty",
        ):
            make_event(component=" ")

    def test_is_frozen(self) -> None:
        event = make_event()

        with self.assertRaises(FrozenInstanceError):
            event.message = "changed"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        self.assertFalse(
            hasattr(
                make_event(),
                "__dict__",
            )
        )


class TimestampTests(unittest.TestCase):
    def test_returns_formatted_timestamp(self) -> None:
        with patch(
            f"{MODULE}.time.strftime",
            return_value="2026-08-05 18:00:00",
        ) as strftime:
            result = timestamp()

        strftime.assert_called_once_with("%Y-%m-%d %H:%M:%S")
        self.assertEqual(
            result,
            "2026-08-05 18:00:00",
        )

    def test_rejects_empty_timestamp(self) -> None:
        with (
            patch(
                f"{MODULE}.time.strftime",
                return_value=" ",
            ),
            self.assertRaisesRegex(
                ValueError,
                "timestamp cannot be empty",
            ),
        ):
            timestamp()


class LogTests(unittest.TestCase):
    def test_creates_directory_and_writes_log(self) -> None:
        file_handle = mock_open()

        with (
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.state_dir),
                "mkdir",
            ) as mkdir,
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.monitor_log),
                "open",
                file_handle,
            ) as open_file,
            patch(
                f"{MODULE}.timestamp",
                return_value="2026-08-05 18:00:00",
            ),
        ):
            log(" monitor started ")

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
        open_file.assert_called_once_with(
            "a",
            encoding="utf-8",
        )
        file_handle().write.assert_called_once_with(
            "2026-08-05 18:00:00 monitor started\n"
        )

    def test_rejects_invalid_message_before_filesystem(self) -> None:
        with (
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.state_dir),
                "mkdir",
            ) as mkdir,
            self.assertRaisesRegex(
                ValueError,
                "message cannot be empty",
            ),
        ):
            log(" ")

        mkdir.assert_not_called()

    def test_filesystem_error_propagates(self) -> None:
        error = OSError("permission denied")

        with (
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.state_dir),
                "mkdir",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            log("monitor started")

        self.assertIs(
            context.exception,
            error,
        )


class WriteEventTests(unittest.TestCase):
    def test_writes_json_event_and_log_entry(self) -> None:
        event = make_event()
        file_handle = mock_open()

        with (
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.state_dir),
                "mkdir",
            ) as mkdir,
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.events_file),
                "open",
                file_handle,
            ),
            patch(f"{MODULE}.log") as log_message,
        ):
            write_event(event)

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )

        payload = json.loads(file_handle().write.call_args.args[0])

        self.assertEqual(
            payload["severity"],
            "warning",
        )
        self.assertEqual(
            payload["event"],
            "system.disk_state",
        )
        log_message.assert_called_once_with(
            ("[WARNING] system: Disk usage changed from 'ok' to 'high'"),
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_rejects_invalid_event_before_filesystem(self) -> None:
        with (
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.state_dir),
                "mkdir",
            ) as mkdir,
            self.assertRaisesRegex(
                TypeError,
                "event must be a MonitorEvent",
            ),
        ):
            write_event(
                object()  # type: ignore[arg-type]
            )

        mkdir.assert_not_called()

    def test_log_error_propagates(self) -> None:
        event = make_event()
        file_handle = mock_open()
        error = OSError("monitor log failed")

        with (
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.state_dir),
                "mkdir",
            ),
            patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths.events_file),
                "open",
                file_handle,
            ),
            patch(
                f"{MODULE}.log",
                side_effect=error,
            ),
            self.assertRaises(OSError) as context,
        ):
            write_event(event)

        self.assertIs(
            context.exception,
            error,
        )


class SeverityForChangeTests(unittest.TestCase):
    def test_battery_states(self) -> None:
        cases = (
            ("critical", "error"),
            ("low", "warning"),
            ("ok", "info"),
        )

        for current, expected in cases:
            with self.subTest(current=current):
                self.assertEqual(
                    severity_for_change(
                        "hardware.battery_state",
                        "ok",
                        current,
                    ),
                    expected,
                )

    def test_availability_changes(self) -> None:
        for path in (
            "hardware.robot_available",
            "hardware.i2c_available",
            "hardware.audio_available",
            "hardware.vision_service_available",
            "hardware.vision_running",
            "hardware.camera_running",
            "hardware.camera_has_frame",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    severity_for_change(
                        path,
                        True,
                        False,
                    ),
                    "error",
                )
                self.assertEqual(
                    severity_for_change(
                        path,
                        False,
                        True,
                    ),
                    "info",
                )

    def test_grayscale_unavailable_is_warning(self) -> None:
        self.assertEqual(
            severity_for_change(
                "hardware.grayscale_available",
                True,
                False,
            ),
            "warning",
        )

    def test_service_inactive_is_error(self) -> None:
        self.assertEqual(
            severity_for_change(
                "services.launchpad.service",
                "active",
                "inactive",
            ),
            "error",
        )

    def test_health_state_severity(self) -> None:
        for suffix in (
            "temperature_state",
            "memory_state",
            "disk_state",
        ):
            with self.subTest(suffix=suffix):
                self.assertEqual(
                    severity_for_change(
                        f"system.{suffix}",
                        "ok",
                        "critical",
                    ),
                    "critical",
                )
                self.assertEqual(
                    severity_for_change(
                        f"system.{suffix}",
                        "ok",
                        "high",
                    ),
                    "warning",
                )

    def test_throttling_severity(self) -> None:
        self.assertEqual(
            severity_for_change(
                "system.undervoltage_now",
                False,
                True,
            ),
            "critical",
        )
        self.assertEqual(
            severity_for_change(
                "system.throttled_now",
                False,
                True,
            ),
            "error",
        )
        self.assertEqual(
            severity_for_change(
                "system.throttled_occurred",
                False,
                True,
            ),
            "warning",
        )

    def test_disconnected_network_is_warning(self) -> None:
        for path in (
            "system.ethernet_connected",
            "system.wifi_connected",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    severity_for_change(
                        path,
                        True,
                        False,
                    ),
                    "warning",
                )

    def test_unknown_change_defaults_to_info(self) -> None:
        self.assertEqual(
            severity_for_change(
                "other.value",
                1,
                2,
            ),
            "info",
        )

    def test_rejects_empty_path(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path cannot be empty",
        ):
            severity_for_change(
                " ",
                None,
                None,
            )


class MessageForChangeTests(unittest.TestCase):
    def test_boolean_availability_message(self) -> None:
        self.assertEqual(
            message_for_change(
                "hardware.audio_available",
                True,
                False,
            ),
            "Audio device became unavailable",
        )

    def test_connected_message(self) -> None:
        self.assertEqual(
            message_for_change(
                "system.wifi_connected",
                False,
                True,
            ),
            "Wi-Fi became connected",
        )

    def test_detected_message(self) -> None:
        self.assertEqual(
            message_for_change(
                "system.undervoltage_now",
                False,
                True,
            ),
            "Undervoltage became detected",
        )

    def test_cleared_message(self) -> None:
        self.assertEqual(
            message_for_change(
                "system.throttled_occurred",
                True,
                False,
            ),
            "Historical throttling became cleared",
        )

    def test_non_boolean_message(self) -> None:
        self.assertEqual(
            message_for_change(
                "system.disk_state",
                "ok",
                "high",
            ),
            "Disk usage changed from 'ok' to 'high'",
        )

    def test_unknown_path_uses_path_as_label(self) -> None:
        self.assertEqual(
            message_for_change(
                "custom.value",
                1,
                2,
            ),
            "custom.value changed from 1 to 2",
        )


class CollectSnapshotTests(unittest.TestCase):
    def test_collects_status_and_system_health(
        self,
    ) -> None:
        status = SimpleNamespace()
        health = Mock()
        health.to_dict.return_value = {
            "temperature": {
                "state": "ok",
            }
        }

        with (
            patch(
                f"{MODULE}.collect_status",
                return_value=status,
            ) as collect_status,
            patch(
                f"{MODULE}.collect_system_health",
                return_value=health,
            ) as collect_health,
            patch(
                f"{MODULE}.asdict",
                return_value={
                    "services": {
                        "launchpad.service": "active",
                    }
                },
            ) as asdict_call,
        ):
            result = collect_snapshot()

        collect_status.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        collect_health.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        asdict_call.assert_called_once_with(status)
        health.to_dict.assert_called_once_with()
        self.assertEqual(
            result["system_health"],
            {
                "temperature": {
                    "state": "ok",
                }
            },
        )

    def test_rejects_invalid_config_before_collection(self) -> None:
        with (
            patch(f"{MODULE}.collect_status") as collect_status,
            self.assertRaisesRegex(
                TypeError,
                "config must be a PlatformConfig",
            ),
        ):
            collect_snapshot(
                object()  # type: ignore[arg-type]
            )

        collect_status.assert_not_called()


class SummarizeTests(unittest.TestCase):
    def test_builds_monitor_summary(self) -> None:
        result = summarize(make_snapshot())

        self.assertEqual(
            result,
            make_summary(),
        )

    def test_missing_sections_use_none_values(self) -> None:
        result = summarize({})

        self.assertEqual(
            result["services"],
            {},
        )
        self.assertIsNone(
            result["hardware"]["battery_state"]  # type: ignore[index]
        )
        self.assertIsNone(
            result["system"]["disk_state"]  # type: ignore[index]
        )

    def test_copies_services_dictionary(self) -> None:
        snapshot = make_snapshot()

        result = summarize(snapshot)

        self.assertIsNot(
            result["services"],
            snapshot["services"],
        )

    def test_rejects_invalid_snapshot(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "snapshot must be a dictionary",
        ):
            summarize(
                []  # type: ignore[arg-type]
            )

    def test_rejects_invalid_nested_hardware(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "snapshot hardware must be a dictionary",
        ):
            summarize(
                {
                    "hardware": [],
                }
            )

    def test_rejects_invalid_nested_section(self) -> None:
        snapshot = make_snapshot()
        snapshot["hardware"]["battery"] = []  # type: ignore[index]

        with self.assertRaisesRegex(
            TypeError,
            "battery must be a dictionary",
        ):
            summarize(snapshot)

    def test_uses_passive_hardware_available(self) -> None:
        result = summarize(make_snapshot())

        self.assertTrue(
            result["hardware"]["robot_available"]  # type: ignore[index]
        )


class FindChangesTests(unittest.TestCase):
    def test_finds_top_level_change(self) -> None:
        result = find_changes(
            {
                "state": "ok",
            },
            {
                "state": "high",
            },
        )

        self.assertEqual(
            result,
            [
                (
                    "state",
                    "ok",
                    "high",
                ),
            ],
        )

    def test_finds_nested_changes(self) -> None:
        result = find_changes(
            {
                "system": {
                    "disk_state": "ok",
                },
            },
            {
                "system": {
                    "disk_state": "high",
                },
            },
        )

        self.assertEqual(
            result,
            [
                (
                    "system.disk_state",
                    "ok",
                    "high",
                ),
            ],
        )

    def test_detects_added_and_removed_keys(self) -> None:
        result = find_changes(
            {
                "old": 1,
            },
            {
                "new": 2,
            },
        )

        self.assertEqual(
            result,
            [
                (
                    "new",
                    None,
                    2,
                ),
                (
                    "old",
                    1,
                    None,
                ),
            ],
        )

    def test_returns_empty_for_equal_values(self) -> None:
        value = make_summary()

        self.assertEqual(
            find_changes(
                value,
                value,
            ),
            [],
        )

    def test_supports_prefix(self) -> None:
        result = find_changes(
            {
                "value": 1,
            },
            {
                "value": 2,
            },
            prefix=" root ",
        )

        self.assertEqual(
            result,
            [
                (
                    "root.value",
                    1,
                    2,
                ),
            ],
        )

    def test_rejects_invalid_previous(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "previous must be a dictionary",
        ):
            find_changes(
                [],  # type: ignore[arg-type]
                {},
            )

    def test_rejects_invalid_prefix(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "prefix must be a string",
        ):
            find_changes(
                {},
                {},
                prefix=1,  # type: ignore[arg-type]
            )

    def test_rejects_non_string_key(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "summary keys must be strings",
        ):
            find_changes(
                {
                    1: "old",
                },
                {
                    1: "new",
                },
            )


class RunOnceTests(unittest.TestCase):
    def test_initial_run_logs_summary(self) -> None:
        snapshot = make_snapshot()
        summary = make_summary()

        with (
            patch(
                f"{MODULE}.collect_snapshot",
                return_value=snapshot,
            ) as collect,
            patch(
                f"{MODULE}.summarize",
                return_value=summary,
            ),
            patch(f"{MODULE}.log") as log_message,
            patch(f"{MODULE}.find_changes") as find_changes_call,
        ):
            result = run_once()

        collect.assert_called_once_with(DEFAULT_PLATFORM_CONFIG)
        self.assertIs(
            result,
            summary,
        )
        find_changes_call.assert_not_called()
        self.assertEqual(
            log_message.call_args_list,
            [
                call(
                    "monitor started",
                    config=DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    (
                        "initial status: "
                        + json.dumps(
                            summary,
                            sort_keys=True,
                        )
                    ),
                    config=DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )

    def test_writes_event_for_each_change(self) -> None:
        previous = make_summary()
        current = make_summary()
        current["system"]["disk_state"] = "high"  # type: ignore[index]

        with (
            patch(
                f"{MODULE}.collect_snapshot",
                return_value=make_snapshot(),
            ),
            patch(
                f"{MODULE}.summarize",
                return_value=current,
            ),
            patch(
                f"{MODULE}.find_changes",
                return_value=[
                    (
                        "system.disk_state",
                        "ok",
                        "high",
                    ),
                ],
            ),
            patch(
                f"{MODULE}.timestamp",
                return_value="2026-08-05 18:00:00",
            ),
            patch(
                f"{MODULE}.severity_for_change",
                return_value="warning",
            ),
            patch(
                f"{MODULE}.message_for_change",
                return_value="Disk usage high",
            ),
            patch(f"{MODULE}.write_event") as write_event_call,
        ):
            result = run_once(previous)

        self.assertIs(
            result,
            current,
        )

        event = write_event_call.call_args.args[0]

        self.assertEqual(
            event.component,
            "system",
        )
        self.assertEqual(
            event.event,
            "system.disk_state",
        )
        self.assertEqual(
            event.previous,
            "ok",
        )
        self.assertEqual(
            event.current,
            "high",
        )
        write_event_call.assert_called_once_with(
            event,
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_no_changes_write_no_events(self) -> None:
        summary = make_summary()

        with (
            patch(
                f"{MODULE}.collect_snapshot",
                return_value=make_snapshot(),
            ),
            patch(
                f"{MODULE}.summarize",
                return_value=summary,
            ),
            patch(
                f"{MODULE}.find_changes",
                return_value=[],
            ),
            patch(f"{MODULE}.write_event") as write_event_call,
        ):
            result = run_once(summary)

        self.assertIs(
            result,
            summary,
        )
        write_event_call.assert_not_called()

    def test_rejects_invalid_previous_summary_before_collection(self) -> None:
        with (
            patch(f"{MODULE}.collect_snapshot") as collect,
            self.assertRaisesRegex(
                TypeError,
                "previous_summary must be a dictionary",
            ),
        ):
            run_once(
                []  # type: ignore[arg-type]
            )

        collect.assert_not_called()


class RunForeverTests(unittest.TestCase):
    def test_uses_configured_interval_by_default(self) -> None:
        configured = DEFAULT_PLATFORM_CONFIG.monitoring.interval_seconds

        with (
            patch(f"{MODULE}.log") as log_message,
            patch(
                f"{MODULE}.run_once",
                side_effect=KeyboardInterrupt,
            ),
            self.assertRaises(KeyboardInterrupt),
        ):
            run_forever()

        log_message.assert_called_once_with(
            (f"monitor loop starting interval={configured}s"),
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_passes_previous_summary_to_next_iteration(self) -> None:
        first = {
            "state": "first",
        }

        with (
            patch(f"{MODULE}.log"),
            patch(
                f"{MODULE}.run_once",
                side_effect=(
                    first,
                    KeyboardInterrupt,
                ),
            ) as run_once_call,
            patch(f"{MODULE}.time.sleep") as sleep,
            self.assertRaises(KeyboardInterrupt),
        ):
            run_forever(2)

        self.assertEqual(
            run_once_call.call_args_list,
            [
                call(
                    None,
                    config=DEFAULT_PLATFORM_CONFIG,
                ),
                call(
                    first,
                    config=DEFAULT_PLATFORM_CONFIG,
                ),
            ],
        )
        sleep.assert_called_once_with(2)

    def test_operational_error_is_logged_and_loop_continues(self) -> None:
        error = OSError("snapshot failed")

        with (
            patch(f"{MODULE}.log") as log_message,
            patch(
                f"{MODULE}.run_once",
                side_effect=(
                    error,
                    KeyboardInterrupt,
                ),
            ),
            patch(f"{MODULE}.time.sleep") as sleep,
            self.assertRaises(KeyboardInterrupt),
        ):
            run_forever(2)

        self.assertIn(
            call(
                "monitor error: snapshot failed",
                config=DEFAULT_PLATFORM_CONFIG,
            ),
            log_message.call_args_list,
        )
        sleep.assert_called_once_with(2)

    def test_error_log_failure_is_suppressed(self) -> None:
        def log_side_effect(
            message: str,
            *,
            config: object,
        ) -> None:
            if message.startswith("monitor error:"):
                raise OSError("log unavailable")

        with (
            patch(
                f"{MODULE}.log",
                side_effect=log_side_effect,
            ),
            patch(
                f"{MODULE}.run_once",
                side_effect=(
                    OSError("snapshot failed"),
                    KeyboardInterrupt,
                ),
            ),
            patch(f"{MODULE}.time.sleep"),
            self.assertRaises(KeyboardInterrupt),
        ):
            run_forever(2)

    def test_unexpected_error_propagates(self) -> None:
        error = AssertionError("programming error")

        with (
            patch(f"{MODULE}.log"),
            patch(
                f"{MODULE}.run_once",
                side_effect=error,
            ),
            self.assertRaises(AssertionError) as context,
        ):
            run_forever(2)

        self.assertIs(
            context.exception,
            error,
        )

    def test_rejects_invalid_interval_before_logging(self) -> None:
        with (
            patch(f"{MODULE}.log") as log_message,
            self.assertRaisesRegex(
                ValueError,
                "interval_seconds must be greater than 0",
            ),
        ):
            run_forever(0)

        log_message.assert_not_called()


class ParserTests(unittest.TestCase):
    def test_builds_parser(self) -> None:
        parser = _build_parser()

        self.assertIsInstance(
            parser,
            argparse.ArgumentParser,
        )
        self.assertEqual(
            parser.prog,
            "betabox monitor",
        )

    def test_default_arguments(self) -> None:
        args = parse_args([])

        self.assertFalse(args.once)
        self.assertIsNone(args.interval)

    def test_parses_once(self) -> None:
        args = parse_args(
            [
                "--once",
            ]
        )

        self.assertTrue(args.once)

    def test_parses_interval(self) -> None:
        args = parse_args(
            [
                "--interval",
                "15",
            ]
        )

        self.assertEqual(
            args.interval,
            15,
        )

    def test_rejects_invalid_interval_syntax(self) -> None:
        with (
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            parse_args(
                [
                    "--interval",
                    "invalid",
                ]
            )

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
    def test_runs_once(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    once=True,
                    interval=None,
                ),
            ) as parse,
            patch(f"{MODULE}.run_once") as run_once_call,
            patch(f"{MODULE}.run_forever") as run_forever_call,
        ):
            result = main(
                [
                    "--once",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        parse.assert_called_once_with(
            [
                "--once",
            ]
        )
        run_once_call.assert_called_once_with(
            config=DEFAULT_PLATFORM_CONFIG,
        )
        run_forever_call.assert_not_called()

    def test_runs_forever_with_configured_interval(self) -> None:
        configured = DEFAULT_PLATFORM_CONFIG.monitoring.interval_seconds

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    once=False,
                    interval=None,
                ),
            ),
            patch(
                f"{MODULE}.run_forever",
                return_value=0,
            ) as run_forever_call,
        ):
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        run_forever_call.assert_called_once_with(
            configured,
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_runs_forever_with_selected_interval(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    once=False,
                    interval=15,
                ),
            ),
            patch(
                f"{MODULE}.run_forever",
                return_value=0,
            ) as run_forever_call,
        ):
            result = main([])

        self.assertEqual(
            result,
            0,
        )
        run_forever_call.assert_called_once_with(
            15,
            config=DEFAULT_PLATFORM_CONFIG,
        )

    def test_reports_operational_error(self) -> None:
        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    once=True,
                    interval=None,
                ),
            ),
            patch(
                f"{MODULE}.run_once",
                side_effect=ValueError("invalid summary"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("monitor failed: invalid summary")

    def test_unexpected_error_propagates(self) -> None:
        error = AssertionError("programming error")

        with (
            patch(
                f"{MODULE}.parse_args",
                return_value=argparse.Namespace(
                    once=True,
                    interval=None,
                ),
            ),
            patch(
                f"{MODULE}.run_once",
                side_effect=error,
            ),
            self.assertRaises(AssertionError) as context,
        ):
            main([])

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
