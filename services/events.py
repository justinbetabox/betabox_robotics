from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)

_SEVERITIES = frozenset(
    {
        "info",
        "warning",
        "error",
        "critical",
    }
)


def _validate_string(
    value: object,
    *,
    name: str,
    default: str | None = None,
) -> str:
    if not isinstance(value, str):
        if default is not None:
            return default

        raise TypeError(f"{name} must be a string")

    result = value.strip()

    if not result:
        if default is not None:
            return default

        raise ValueError(f"{name} cannot be empty")

    return result


def _validate_optional_filter(
    value: object,
    *,
    name: str,
) -> str | None:
    if value is None:
        return None

    return _validate_string(
        value,
        name=name,
    ).casefold()


def _validate_last(
    value: object,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError("last must be an integer or None")

    if value < 0:
        raise ValueError("last cannot be negative")

    return value


@dataclass(frozen=True, slots=True)
class EventRecord:
    """
    One event recorded by the Betabox Platform.
    """

    timestamp: str
    severity: str
    component: str
    message: str

    event: str | None = None
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        timestamp = _validate_string(
            self.timestamp,
            name="timestamp",
            default="unknown time",
        )
        severity = normalize_severity(self.severity)
        component = _validate_string(
            self.component,
            name="component",
            default="unknown",
        )
        message = _validate_string(
            self.message,
            name="message",
            default="unknown event",
        )

        event_name = self.event

        if event_name is not None:
            if not isinstance(
                event_name,
                str,
            ):
                raise TypeError("event must be a string or None")

            event_name = event_name.strip() or None

        details = self.details

        if details is not None:
            if not isinstance(
                details,
                Mapping,
            ):
                raise TypeError("details must be a mapping or None")

            details = MappingProxyType(dict(details))

        object.__setattr__(
            self,
            "timestamp",
            timestamp,
        )
        object.__setattr__(
            self,
            "severity",
            severity,
        )
        object.__setattr__(
            self,
            "component",
            component,
        )
        object.__setattr__(
            self,
            "message",
            message,
        )
        object.__setattr__(
            self,
            "event",
            event_name,
        )
        object.__setattr__(
            self,
            "details",
            details,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "component": self.component,
            "message": self.message,
            "event": self.event,
            "details": (None if self.details is None else dict(self.details)),
        }


@dataclass(frozen=True, slots=True)
class EventReport:
    """
    Collection of recent platform events and summary information.
    """

    events: tuple[EventRecord, ...]
    total_available: int
    components: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.events,
            tuple,
        ):
            raise TypeError("events must be a tuple")

        if not all(isinstance(event, EventRecord) for event in self.events):
            raise TypeError("events must contain only EventRecord instances")

        if isinstance(self.total_available, bool) or not isinstance(
            self.total_available,
            int,
        ):
            raise TypeError("total_available must be an integer")

        if self.total_available < 0:
            raise ValueError("total_available cannot be negative")

        if self.total_available < len(self.events):
            raise ValueError("total_available cannot be less than the number of events")

        if not isinstance(
            self.components,
            tuple,
        ):
            raise TypeError("components must be a tuple")

        components = tuple(
            _validate_string(
                component,
                name="component",
            )
            for component in self.components
        )

        object.__setattr__(
            self,
            "components",
            components,
        )

    @property
    def total(self) -> int:
        return len(self.events)

    def _count_severity(
        self,
        severity: str,
    ) -> int:
        return sum(event.severity == severity for event in self.events)

    @property
    def info(self) -> int:
        return self._count_severity("info")

    @property
    def warning(self) -> int:
        return self._count_severity("warning")

    @property
    def error(self) -> int:
        return self._count_severity("error")

    @property
    def critical(self) -> int:
        return self._count_severity("critical")

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "total": self.total,
                "total_available": self.total_available,
                "info": self.info,
                "warning": self.warning,
                "error": self.error,
                "critical": self.critical,
            },
            "components": list(self.components),
            "events": [event.to_dict() for event in self.events],
        }


def normalize_severity(
    value: object,
) -> str:
    if not isinstance(value, str):
        return "info"

    severity = value.strip().casefold()

    if severity not in _SEVERITIES:
        return "info"

    return severity


def event_from_dict(
    payload: Mapping[str, Any],
) -> EventRecord:
    """
    Convert a decoded JSON event into a stable event record.
    """

    if not isinstance(
        payload,
        Mapping,
    ):
        raise TypeError("payload must be a mapping")

    timestamp_value = payload.get("timestamp")
    timestamp = (
        timestamp_value.strip()
        if isinstance(
            timestamp_value,
            str,
        )
        and timestamp_value.strip()
        else "unknown time"
    )

    component_value = payload.get("component")
    component = (
        component_value.strip()
        if isinstance(
            component_value,
            str,
        )
        and component_value.strip()
        else "unknown"
    )

    message_value = payload.get(
        "message",
        payload.get("event"),
    )
    message = (
        message_value.strip()
        if isinstance(
            message_value,
            str,
        )
        and message_value.strip()
        else "unknown event"
    )

    event_value = payload.get("event")
    event_name = (
        event_value.strip()
        if isinstance(
            event_value,
            str,
        )
        and event_value.strip()
        else None
    )

    details_value = payload.get("details")
    details = (
        dict(details_value)
        if isinstance(
            details_value,
            Mapping,
        )
        else None
    )

    return EventRecord(
        timestamp=timestamp,
        severity=normalize_severity(payload.get("severity")),
        component=component,
        message=message,
        event=event_name,
        details=details,
    )


def read_events(
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> list[EventRecord]:
    """
    Read valid events from the platform JSONL event log.
    """

    if not isinstance(
        config,
        PlatformConfig,
    ):
        raise TypeError("config must be a PlatformConfig")

    events_file = config.paths.events_file

    if not events_file.is_file():
        return []

    events: list[EventRecord] = []

    try:
        with events_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(
                    payload,
                    dict,
                ):
                    continue

                events.append(event_from_dict(payload))
    except OSError:
        return []

    return events


def timestamp_sort_key(
    event: EventRecord,
) -> tuple[int, str]:
    """
    Return a stable sort key for valid and malformed timestamps.
    """

    if not isinstance(
        event,
        EventRecord,
    ):
        raise TypeError("event must be an EventRecord")

    try:
        parsed = datetime.fromisoformat(event.timestamp)
    except ValueError:
        return (
            0,
            event.timestamp,
        )

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC)

    return (
        1,
        parsed.isoformat(),
    )


def filter_events(
    events: Sequence[EventRecord],
    *,
    severity: str | None = None,
    component: str | None = None,
) -> list[EventRecord]:
    if isinstance(
        events,
        str | bytes,
    ) or not isinstance(
        events,
        Sequence,
    ):
        raise TypeError("events must be a sequence")

    if not all(isinstance(event, EventRecord) for event in events):
        raise TypeError("events must contain only EventRecord instances")

    requested_severity = _validate_optional_filter(
        severity,
        name="severity",
    )
    requested_component = _validate_optional_filter(
        component,
        name="component",
    )

    if requested_severity is not None and requested_severity not in _SEVERITIES:
        raise ValueError("severity must be info, warning, error, or critical")

    return [
        event
        for event in events
        if (requested_severity is None or event.severity == requested_severity)
        and (
            requested_component is None
            or event.component.casefold() == requested_component
        )
    ]


def collect_event_report(
    *,
    last: int | None = None,
    severity: str | None = None,
    component: str | None = None,
    config: PlatformConfig = DEFAULT_PLATFORM_CONFIG,
) -> EventReport:
    """
    Collect recent events for CLI and Launchpad consumers.

    Events are returned newest first.
    """

    last_value = _validate_last(last)

    events = read_events(config)

    components = sorted(
        {event.component for event in events},
        key=str.casefold,
    )

    filtered = filter_events(
        events,
        severity=severity,
        component=component,
    )

    filtered = sorted(
        filtered,
        key=timestamp_sort_key,
        reverse=True,
    )

    total_available = len(filtered)

    if last_value is not None:
        filtered = filtered[:last_value]

    return EventReport(
        events=tuple(filtered),
        total_available=total_available,
        components=tuple(components),
    )


def print_events(
    report: EventReport,
) -> None:
    if not isinstance(
        report,
        EventReport,
    ):
        raise TypeError("report must be an EventReport")

    print()
    print("Betabox Events")
    print("==============")
    print()

    if not report.events:
        print("No events found.")
        print()
        return

    for event in report.events:
        print(
            f"{event.timestamp}  "
            f"[{event.severity.upper():8}] "
            f"{event.component}: "
            f"{event.message}"
        )

    print()


def main(
    argv: list[str] | None = None,
) -> int:
    config = DEFAULT_PLATFORM_CONFIG

    parser = argparse.ArgumentParser(prog="betabox events")

    parser.add_argument(
        "--last",
        type=int,
        default=(config.monitoring.default_event_count),
        help=("Show the most recent events"),
    )

    parser.add_argument(
        "--severity",
        choices=[
            "info",
            "warning",
            "error",
            "critical",
        ],
        help=("Show only events with this severity"),
    )

    parser.add_argument(
        "--component",
        help=("Show only events from this component"),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=("Output the event report as JSON"),
    )

    args = parser.parse_args(argv)

    try:
        report = collect_event_report(
            last=args.last,
            severity=args.severity,
            component=args.component,
            config=config,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        print(str(exc))
        return 1

    if args.json:
        print(
            json.dumps(
                report.to_dict(),
                indent=2,
            )
        )
    else:
        print_events(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
