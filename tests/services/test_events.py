from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType
from unittest.mock import (
    PropertyMock,
    call,
    patch,
)

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.events import (
    EventRecord,
    EventReport,
    _validate_last,
    _validate_optional_filter,
    _validate_string,
    collect_event_report,
    event_from_dict,
    filter_events,
    main,
    normalize_severity,
    print_events,
    read_events,
    timestamp_sort_key,
)

MODULE = "betabox_robotics.services.events"


def make_event(
    *,
    timestamp: str = "2026-08-05T12:00:00Z",
    severity: str = "info",
    component: str = "monitor",
    message: str = "Platform healthy",
    event: str | None = "platform_healthy",
    details: Mapping[str, object] | None = None,
) -> EventRecord:
    return EventRecord(
        timestamp=timestamp,
        severity=severity,
        component=component,
        message=message,
        event=event,
        details=details,
    )


class ValidateStringTests(unittest.TestCase):
    def test_accepts_and_normalizes_string(self) -> None:
        self.assertEqual(
            _validate_string(
                " monitor ",
                name="component",
            ),
            "monitor",
        )

    def test_uses_default_for_invalid_type(self) -> None:
        self.assertEqual(
            _validate_string(
                123,
                name="component",
                default="unknown",
            ),
            "unknown",
        )

    def test_uses_default_for_empty_string(self) -> None:
        self.assertEqual(
            _validate_string(
                " ",
                name="component",
                default="unknown",
            ),
            "unknown",
        )

    def test_rejects_invalid_type_without_default(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "component must be a string",
        ):
            _validate_string(
                123,
                name="component",
            )

    def test_rejects_empty_string_without_default(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "component cannot be empty",
        ):
            _validate_string(
                " ",
                name="component",
            )


class ValidateOptionalFilterTests(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(
            _validate_optional_filter(
                None,
                name="component",
            )
        )

    def test_normalizes_and_casefolds(self) -> None:
        self.assertEqual(
            _validate_optional_filter(
                " MONITOR ",
                name="component",
            ),
            "monitor",
        )

    def test_rejects_empty_filter(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "component cannot be empty",
        ):
            _validate_optional_filter(
                " ",
                name="component",
            )


class ValidateLastTests(unittest.TestCase):
    def test_accepts_none(self) -> None:
        self.assertIsNone(_validate_last(None))

    def test_accepts_zero(self) -> None:
        self.assertEqual(
            _validate_last(0),
            0,
        )

    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_last(10),
            10,
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            1.0,
            "1",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "last must be an integer or None",
                ),
            ):
                _validate_last(value)

    def test_rejects_negative_value(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "last cannot be negative",
        ):
            _validate_last(-1)


class EventRecordTests(unittest.TestCase):
    def test_create(self) -> None:
        details = {
            "temperature": 45.2,
        }

        record = make_event(details=details)

        self.assertEqual(
            record.timestamp,
            "2026-08-05T12:00:00Z",
        )
        self.assertEqual(
            record.severity,
            "info",
        )
        self.assertEqual(
            record.component,
            "monitor",
        )
        self.assertEqual(
            record.message,
            "Platform healthy",
        )
        self.assertEqual(
            record.event,
            "platform_healthy",
        )
        self.assertEqual(
            dict(record.details or {}),
            details,
        )

    def test_normalizes_fields(self) -> None:
        record = EventRecord(
            timestamp=" 2026-08-05T12:00:00Z ",
            severity=" WARNING ",
            component=" Monitor ",
            message=" Temperature elevated ",
            event=" temperature_warning ",
        )

        self.assertEqual(
            record.timestamp,
            "2026-08-05T12:00:00Z",
        )
        self.assertEqual(
            record.severity,
            "warning",
        )
        self.assertEqual(
            record.component,
            "Monitor",
        )
        self.assertEqual(
            record.message,
            "Temperature elevated",
        )
        self.assertEqual(
            record.event,
            "temperature_warning",
        )

    def test_uses_fallback_text(self) -> None:
        record = EventRecord(
            timestamp=" ",
            severity="invalid",
            component=" ",
            message=" ",
            event=" ",
        )

        self.assertEqual(
            record.timestamp,
            "unknown time",
        )
        self.assertEqual(
            record.severity,
            "info",
        )
        self.assertEqual(
            record.component,
            "unknown",
        )
        self.assertEqual(
            record.message,
            "unknown event",
        )
        self.assertIsNone(record.event)

    def test_details_are_copied_and_immutable(self) -> None:
        original = {
            "value": 1,
        }

        record = make_event(details=original)

        original["value"] = 2

        self.assertEqual(
            record.details,
            {
                "value": 1,
            },
        )
        self.assertIsInstance(
            record.details,
            MappingProxyType,
        )

        with self.assertRaises(TypeError):
            record.details["value"] = 3  # type: ignore[index]

    def test_rejects_invalid_event_name(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "event must be a string or None",
        ):
            make_event(
                event=123,  # type: ignore[arg-type]
            )

    def test_rejects_invalid_details(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "details must be a mapping or None",
        ):
            make_event(
                details=[  # type: ignore[arg-type]
                    "invalid",
                ]
            )

    def test_to_dict_returns_mutable_copy(self) -> None:
        record = make_event(
            details={
                "value": 1,
            }
        )

        value = record.to_dict()

        self.assertEqual(
            value,
            {
                "timestamp": "2026-08-05T12:00:00Z",
                "severity": "info",
                "component": "monitor",
                "message": "Platform healthy",
                "event": "platform_healthy",
                "details": {
                    "value": 1,
                },
            },
        )

        details = value["details"]

        self.assertIsInstance(
            details,
            dict,
        )

        details["value"] = 2

        self.assertEqual(
            record.details,
            {
                "value": 1,
            },
        )

    def test_is_frozen(self) -> None:
        record = make_event()

        with self.assertRaises(FrozenInstanceError):
            record.message = "Changed"  # type: ignore[misc]


class EventReportTests(unittest.TestCase):
    def test_counts_and_serializes_events(self) -> None:
        events = (
            make_event(severity="info"),
            make_event(severity="warning"),
            make_event(severity="error"),
            make_event(severity="critical"),
            make_event(severity="error"),
        )

        report = EventReport(
            events=events,
            total_available=8,
            components=(
                "monitor",
                "video",
            ),
        )

        self.assertEqual(
            report.total,
            5,
        )
        self.assertEqual(
            report.info,
            1,
        )
        self.assertEqual(
            report.warning,
            1,
        )
        self.assertEqual(
            report.error,
            2,
        )
        self.assertEqual(
            report.critical,
            1,
        )

        value = report.to_dict()

        self.assertEqual(
            value["summary"],
            {
                "total": 5,
                "total_available": 8,
                "info": 1,
                "warning": 1,
                "error": 2,
                "critical": 1,
            },
        )
        self.assertEqual(
            value["components"],
            [
                "monitor",
                "video",
            ],
        )
        self.assertEqual(
            len(value["events"]),
            5,
        )

    def test_normalizes_components(self) -> None:
        report = EventReport(
            events=(),
            total_available=0,
            components=(" monitor ",),
        )

        self.assertEqual(
            report.components,
            ("monitor",),
        )

    def test_rejects_non_tuple_events(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "events must be a tuple",
        ):
            EventReport(
                events=[],  # type: ignore[arg-type]
                total_available=0,
                components=(),
            )

    def test_rejects_invalid_event_entry(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "events must contain only EventRecord instances",
        ):
            EventReport(
                events=(
                    object(),  # type: ignore[arg-type]
                ),
                total_available=1,
                components=(),
            )

    def test_rejects_invalid_total_available_type(
        self,
    ) -> None:
        for value in (
            True,
            1.0,
            "1",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "total_available must be an integer",
                ),
            ):
                EventReport(
                    events=(),
                    total_available=value,  # type: ignore[arg-type]
                    components=(),
                )

    def test_rejects_negative_total_available(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "total_available cannot be negative",
        ):
            EventReport(
                events=(),
                total_available=-1,
                components=(),
            )

    def test_rejects_total_less_than_returned_events(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "total_available cannot be less than",
        ):
            EventReport(
                events=(make_event(),),
                total_available=0,
                components=(),
            )

    def test_rejects_non_tuple_components(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "components must be a tuple",
        ):
            EventReport(
                events=(),
                total_available=0,
                components=[],  # type: ignore[arg-type]
            )


class NormalizeSeverityTests(unittest.TestCase):
    def test_accepts_supported_values(self) -> None:
        for value in (
            "info",
            "warning",
            "error",
            "critical",
            " WARNING ",
        ):
            with self.subTest(value=value):
                expected = value.strip().casefold()

                self.assertEqual(
                    normalize_severity(value),
                    expected,
                )

    def test_invalid_values_fall_back_to_info(
        self,
    ) -> None:
        for value in (
            "debug",
            "",
            " ",
            None,
            123,
            object(),
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_severity(value),
                    "info",
                )


class EventFromDictTests(unittest.TestCase):
    def test_converts_complete_payload(self) -> None:
        record = event_from_dict(
            {
                "timestamp": (" 2026-08-05T12:00:00Z "),
                "severity": " WARNING ",
                "component": " monitor ",
                "message": (" CPU temperature elevated "),
                "event": " cpu_warning ",
                "details": {
                    "temperature": 80,
                },
            }
        )

        self.assertEqual(
            record.timestamp,
            "2026-08-05T12:00:00Z",
        )
        self.assertEqual(
            record.severity,
            "warning",
        )
        self.assertEqual(
            record.component,
            "monitor",
        )
        self.assertEqual(
            record.message,
            "CPU temperature elevated",
        )
        self.assertEqual(
            record.event,
            "cpu_warning",
        )
        self.assertEqual(
            record.details,
            {
                "temperature": 80,
            },
        )

    def test_message_falls_back_to_event(self) -> None:
        record = event_from_dict(
            {
                "event": "robot_started",
            }
        )

        self.assertEqual(
            record.message,
            "robot_started",
        )

    def test_missing_values_use_defaults(self) -> None:
        record = event_from_dict({})

        self.assertEqual(
            record.timestamp,
            "unknown time",
        )
        self.assertEqual(
            record.severity,
            "info",
        )
        self.assertEqual(
            record.component,
            "unknown",
        )
        self.assertEqual(
            record.message,
            "unknown event",
        )
        self.assertIsNone(record.event)
        self.assertIsNone(record.details)

    def test_invalid_details_are_ignored(self) -> None:
        record = event_from_dict(
            {
                "details": [
                    "invalid",
                ],
            }
        )

        self.assertIsNone(record.details)

    def test_rejects_non_mapping(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "payload must be a mapping",
        ):
            event_from_dict(
                []  # type: ignore[arg-type]
            )


class ReadEventsTests(unittest.TestCase):
    def test_reads_valid_events_and_skips_invalid_lines(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            events_file = Path(temp_dir) / "events.jsonl"

            events_file.write_text(
                "\n".join(
                    [
                        "",
                        json.dumps(
                            {
                                "timestamp": ("2026-08-05T12:00:00Z"),
                                "severity": "info",
                                "component": "monitor",
                                "message": "Healthy",
                            }
                        ),
                        "{invalid json",
                        json.dumps(
                            [
                                "not",
                                "a",
                                "mapping",
                            ]
                        ),
                        json.dumps(
                            {
                                "timestamp": ("2026-08-05T12:05:00Z"),
                                "severity": "error",
                                "component": "video",
                                "message": "Camera failed",
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths),
                "events_file",
                new_callable=PropertyMock,
                return_value=events_file,
            ):
                events = read_events()

        self.assertEqual(
            len(events),
            2,
        )
        self.assertEqual(
            events[0].message,
            "Healthy",
        )
        self.assertEqual(
            events[1].message,
            "Camera failed",
        )

    def test_returns_empty_list_for_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            events_file = Path(temp_dir) / "missing.jsonl"

            with patch.object(
                type(DEFAULT_PLATFORM_CONFIG.paths),
                "events_file",
                new_callable=PropertyMock,
                return_value=events_file,
            ):
                result = read_events()

        self.assertEqual(
            result,
            [],
        )

    def test_returns_empty_list_for_read_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            events_file = Path(temp_dir) / "events.jsonl"
            events_file.touch()

            with (
                patch.object(
                    type(DEFAULT_PLATFORM_CONFIG.paths),
                    "events_file",
                    new_callable=PropertyMock,
                    return_value=events_file,
                ),
                patch.object(
                    Path,
                    "open",
                    side_effect=OSError("permission denied"),
                ),
            ):
                result = read_events()

        self.assertEqual(
            result,
            [],
        )

    def test_rejects_invalid_config(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "config must be a PlatformConfig",
        ):
            read_events(
                object()  # type: ignore[arg-type]
            )


class TimestampSortKeyTests(unittest.TestCase):
    def test_normalizes_utc_z_timestamp(self) -> None:
        key = timestamp_sort_key(make_event(timestamp=("2026-08-05T12:00:00Z")))

        self.assertEqual(
            key,
            (
                1,
                "2026-08-05T12:00:00+00:00",
            ),
        )

    def test_normalizes_offset_timestamp_to_utc(
        self,
    ) -> None:
        key = timestamp_sort_key(make_event(timestamp=("2026-08-05T08:00:00-04:00")))

        self.assertEqual(
            key,
            (
                1,
                "2026-08-05T12:00:00+00:00",
            ),
        )

    def test_preserves_naive_timestamp(self) -> None:
        key = timestamp_sort_key(make_event(timestamp=("2026-08-05T12:00:00")))

        self.assertEqual(
            key,
            (
                1,
                "2026-08-05T12:00:00",
            ),
        )

    def test_malformed_timestamp_sorts_as_invalid(
        self,
    ) -> None:
        key = timestamp_sort_key(make_event(timestamp="unknown time"))

        self.assertEqual(
            key,
            (
                0,
                "unknown time",
            ),
        )

    def test_rejects_invalid_event(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "event must be an EventRecord",
        ):
            timestamp_sort_key(
                object()  # type: ignore[arg-type]
            )


class FilterEventsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = [
            make_event(
                severity="info",
                component="Monitor",
                message="Healthy",
            ),
            make_event(
                severity="warning",
                component="Monitor",
                message="Warm",
            ),
            make_event(
                severity="error",
                component="Video",
                message="Camera failed",
            ),
        ]

    def test_no_filters_returns_all_events(self) -> None:
        result = filter_events(self.events)

        self.assertEqual(
            result,
            self.events,
        )
        self.assertIsNot(
            result,
            self.events,
        )

    def test_filters_by_severity(self) -> None:
        result = filter_events(
            self.events,
            severity=" WARNING ",
        )

        self.assertEqual(
            [event.message for event in result],
            [
                "Warm",
            ],
        )

    def test_filters_component_case_insensitively(
        self,
    ) -> None:
        result = filter_events(
            self.events,
            component=" monitor ",
        )

        self.assertEqual(
            [event.message for event in result],
            [
                "Healthy",
                "Warm",
            ],
        )

    def test_combines_filters(self) -> None:
        result = filter_events(
            self.events,
            severity="error",
            component="video",
        )

        self.assertEqual(
            [event.message for event in result],
            [
                "Camera failed",
            ],
        )

    def test_rejects_invalid_severity(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            ("severity must be info, warning, error, or critical"),
        ):
            filter_events(
                self.events,
                severity="debug",
            )

    def test_rejects_non_sequence(self) -> None:
        for value in (
            "events",
            b"events",
            123,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "events must be a sequence",
                ),
            ):
                filter_events(
                    value  # type: ignore[arg-type]
                )

    def test_rejects_invalid_sequence_entry(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            ("events must contain only EventRecord instances"),
        ):
            filter_events(
                [
                    object(),  # type: ignore[list-item]
                ]
            )


class CollectEventReportTests(unittest.TestCase):
    def test_sorts_newest_first_and_collects_components(
        self,
    ) -> None:
        events = [
            make_event(
                timestamp="2026-08-05T11:00:00Z",
                component="Video",
                message="Older",
            ),
            make_event(
                timestamp="2026-08-05T12:00:00Z",
                component="Monitor",
                message="Newest",
            ),
            make_event(
                timestamp="not-a-time",
                component="Video",
                message="Malformed",
            ),
        ]

        with patch(
            f"{MODULE}.read_events",
            return_value=events,
        ):
            report = collect_event_report()

        self.assertEqual(
            [event.message for event in report.events],
            [
                "Newest",
                "Older",
                "Malformed",
            ],
        )
        self.assertEqual(
            report.components,
            (
                "Monitor",
                "Video",
            ),
        )
        self.assertEqual(
            report.total_available,
            3,
        )

    def test_applies_filters_before_total_available(
        self,
    ) -> None:
        events = [
            make_event(
                severity="warning",
                component="monitor",
            ),
            make_event(
                severity="error",
                component="video",
            ),
        ]

        with patch(
            f"{MODULE}.read_events",
            return_value=events,
        ):
            report = collect_event_report(severity="error")

        self.assertEqual(
            report.total_available,
            1,
        )
        self.assertEqual(
            len(report.events),
            1,
        )
        self.assertEqual(
            report.events[0].severity,
            "error",
        )

    def test_limits_returned_events(self) -> None:
        events = [
            make_event(
                timestamp=(f"2026-08-05T12:00:0{index}Z"),
                message=str(index),
            )
            for index in range(3)
        ]

        with patch(
            f"{MODULE}.read_events",
            return_value=events,
        ):
            report = collect_event_report(last=2)

        self.assertEqual(
            report.total,
            2,
        )
        self.assertEqual(
            report.total_available,
            3,
        )

    def test_last_zero_returns_empty_report(self) -> None:
        with patch(
            f"{MODULE}.read_events",
            return_value=[
                make_event(),
            ],
        ):
            report = collect_event_report(last=0)

        self.assertEqual(
            report.events,
            (),
        )
        self.assertEqual(
            report.total_available,
            1,
        )

    def test_validates_last_before_reading_events(
        self,
    ) -> None:
        with (
            patch(f"{MODULE}.read_events") as read,
            self.assertRaisesRegex(
                TypeError,
                "last must be an integer or None",
            ),
        ):
            collect_event_report(last=True)

        read.assert_not_called()


class PrintEventsTests(unittest.TestCase):
    def test_prints_events(self) -> None:
        report = EventReport(
            events=(
                make_event(
                    timestamp=("2026-08-05T12:00:00Z"),
                    severity="warning",
                    component="monitor",
                    message=("Temperature elevated"),
                ),
            ),
            total_available=1,
            components=("monitor",),
        )

        with patch("builtins.print") as print_message:
            print_events(report)

        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Events"),
                call("=============="),
                call(),
                call("2026-08-05T12:00:00Z  [WARNING ] monitor: Temperature elevated"),
                call(),
            ],
        )

    def test_prints_empty_report_message(self) -> None:
        report = EventReport(
            events=(),
            total_available=0,
            components=(),
        )

        with patch("builtins.print") as print_message:
            print_events(report)

        self.assertIn(
            call("No events found."),
            print_message.call_args_list,
        )

    def test_rejects_invalid_report(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "report must be an EventReport",
        ):
            print_events(
                object()  # type: ignore[arg-type]
            )


class MainTests(unittest.TestCase):
    def test_forwards_arguments_and_prints_text(
        self,
    ) -> None:
        report = EventReport(
            events=(),
            total_available=0,
            components=(),
        )

        with (
            patch(
                f"{MODULE}.collect_event_report",
                return_value=report,
            ) as collect,
            patch(f"{MODULE}.print_events") as print_report,
        ):
            result = main(
                [
                    "--last",
                    "5",
                    "--severity",
                    "warning",
                    "--component",
                    "monitor",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        collect.assert_called_once_with(
            last=5,
            severity="warning",
            component="monitor",
            config=DEFAULT_PLATFORM_CONFIG,
        )
        print_report.assert_called_once_with(report)

    def test_prints_json_report(self) -> None:
        report = EventReport(
            events=(),
            total_available=0,
            components=(),
        )

        with (
            patch(
                f"{MODULE}.collect_event_report",
                return_value=report,
            ),
            patch("builtins.print") as print_message,
        ):
            result = main(
                [
                    "--json",
                ]
            )

        self.assertEqual(
            result,
            0,
        )
        print_message.assert_called_once_with(
            json.dumps(
                report.to_dict(),
                indent=2,
            )
        )

    def test_returns_one_for_value_error(self) -> None:
        with (
            patch(
                f"{MODULE}.collect_event_report",
                side_effect=ValueError("last cannot be negative"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("last cannot be negative")

    def test_returns_one_for_type_error(self) -> None:
        with (
            patch(
                f"{MODULE}.collect_event_report",
                side_effect=TypeError("invalid input"),
            ),
            patch("builtins.print") as print_message,
        ):
            result = main([])

        self.assertEqual(
            result,
            1,
        )
        print_message.assert_called_once_with("invalid input")

    def test_unexpected_error_propagates(self) -> None:
        error = RuntimeError("event service failed")

        with (
            patch(
                f"{MODULE}.collect_event_report",
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
