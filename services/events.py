from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EVENTS_FILE = (
    Path.home()
    / ".local"
    / "state"
    / "betabox"
    / "events.jsonl"
)


def read_events() -> list[dict[str, Any]]:
    if not EVENTS_FILE.exists():
        return []

    events: list[dict[str, Any]] = []

    with EVENTS_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # Ignore incomplete or damaged lines rather than
                # breaking the entire events command.
                continue

            if isinstance(event, dict):
                events.append(event)

    return events

def filter_events(
    events: list[dict[str, Any]],
    *,
    severity: str | None = None,
    component: str | None = None,
) -> list[dict[str, Any]]:
    filtered = events

    if severity is not None:
        severity = severity.lower()

        filtered = [
            event
            for event in filtered
            if str(event.get("severity", "")).lower() == severity
        ]

    if component is not None:
        component = component.lower()

        filtered = [
            event
            for event in filtered
            if str(event.get("component", "")).lower() == component
        ]

    return filtered

def print_events(events: list[dict[str, Any]]) -> None:
    print()
    print("Betabox Events")
    print("==============")
    print()

    if not events:
        print("No events found.")
        print()
        return

    for event in events:
        timestamp = event.get("timestamp", "unknown time")
        severity = str(event.get("severity", "info")).upper()
        component = event.get("component", "unknown")
        message = event.get("message", event.get("event", "unknown event"))

        print(
            f"{timestamp}  "
            f"[{severity:8}] "
            f"{component}: {message}"
        )

    print()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betabox events")

    parser.add_argument(
        "--last",
        type=int,
        default=20,
        help="Show the most recent events",
    )

    parser.add_argument(
        "--severity",
        choices=["info", "warning", "error", "critical"],
        help="Show only events with this severity",
    )

    parser.add_argument(
        "--component",
        help="Show only events from this component",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output events as JSON",
    )

    args = parser.parse_args(argv)

    events = read_events()
    events = filter_events(
        events,
        severity=args.severity,
        component=args.component,
    )

    if args.last is not None and args.last >= 0:
        events = events[-args.last:]

    if args.json:
        print(json.dumps(events, indent=2))
    else:
        print_events(events)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
