from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
    PlatformConfig,
)


@dataclass(frozen=True)
class EventRecord:
    """
    One event recorded by the Betabox Platform.
    """

    timestamp: str
    severity: str
    component: str
    message: str

    event: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventReport:
    """
    Collection of recent platform events and summary information.
    """

    events: list[EventRecord]
    total_available: int
    components: list[str]

    @property
    def total(self) -> int:
        return len(self.events)

    @property
    def info(self) -> int:
        return sum(
            1
            for event in self.events
            if event.severity == "info"
        )

    @property
    def warning(self) -> int:
        return sum(
            1
            for event in self.events
            if event.severity == "warning"
        )

    @property
    def error(self) -> int:
        return sum(
            1
            for event in self.events
            if event.severity == "error"
        )

    @property
    def critical(self) -> int:
        return sum(
            1
            for event in self.events
            if event.severity == "critical"
        )

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
            "components": self.components,
            "events": [
                event.to_dict()
                for event in self.events
            ],
        }


def normalize_severity(
    value: object,
) -> str:
    severity = str(
        value or "info"
    ).strip().lower()

    if severity not in {
        "info",
        "warning",
        "error",
        "critical",
    }:
        return "info"

    return severity


def event_from_dict(
    payload: dict[str, Any],
) -> EventRecord:
    """
    Convert a decoded JSON event into a stable event record.
    """

    timestamp = str(
        payload.get(
            "timestamp",
            "unknown time",
        )
    )

    severity = normalize_severity(
        payload.get("severity")
    )

    component = str(
        payload.get(
            "component",
            "unknown",
        )
    ).strip() or "unknown"

    message = str(
        payload.get(
            "message",
            payload.get(
                "event",
                "unknown event",
            ),
        )
    ).strip() or "unknown event"

    event_name = payload.get("event")

    if event_name is not None:
        event_name = str(event_name)

    details = payload.get("details")

    if not isinstance(details, dict):
        details = None

    return EventRecord(
        timestamp=timestamp,
        severity=severity,
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

    events_file = config.paths.events_file

    if not events_file.exists():
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

                events.append(
                    event_from_dict(payload)
                )
    except OSError:
        return []

    return events


def timestamp_sort_key(
    event: EventRecord,
) -> tuple[int, datetime | str]:
    """
    Return a stable sort key for valid and malformed timestamps.
    """

    try:
        timestamp = datetime.fromisoformat(
            event.timestamp.replace(
                "Z",
                "+00:00",
            )
        )

        return (
            1,
            timestamp,
        )
    except ValueError:
        return (
            0,
            event.timestamp,
        )


def filter_events(
    events: list[EventRecord],
    *,
    severity: str | None = None,
    component: str | None = None,
) -> list[EventRecord]:
    filtered = events

    if severity is not None:
        requested_severity = (
            severity.strip().lower()
        )

        filtered = [
            event
            for event in filtered
            if event.severity
            == requested_severity
        ]

    if component is not None:
        requested_component = (
            component.strip().lower()
        )

        filtered = [
            event
            for event in filtered
            if event.component.lower()
            == requested_component
        ]

    return filtered


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

    events = read_events(
        config
    )

    components = sorted(
        {
            event.component
            for event in events
        },
        key=str.lower,
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

    if last is not None:
        if last < 0:
            raise ValueError(
                "last cannot be negative"
            )

        filtered = filtered[:last]

    return EventReport(
        events=filtered,
        total_available=total_available,
        components=components,
    )


def print_events(
    report: EventReport,
) -> None:
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

    parser = argparse.ArgumentParser(
        prog="betabox events"
    )

    parser.add_argument(
        "--last",
        type=int,
        default=(
            config.monitoring
            .default_event_count
        ),
        help=(
            "Show the most recent events"
        ),
    )

    parser.add_argument(
        "--severity",
        choices=[
            "info",
            "warning",
            "error",
            "critical",
        ],
        help=(
            "Show only events with this severity"
        ),
    )

    parser.add_argument(
        "--component",
        help=(
            "Show only events from this component"
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Output the event report as JSON"
        ),
    )

    args = parser.parse_args(
        argv
    )

    try:
        report = collect_event_report(
            last=args.last,
            severity=args.severity,
            component=args.component,
            config=config,
        )
    except ValueError as exc:
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
        print_events(
            report
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
