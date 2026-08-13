from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

Payload = dict[str, object]
Collector = Callable[[], Payload]


def _validate_ttl(
    value: object,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        int | float,
    ):
        raise TypeError("ttl_seconds must be a number")

    result = float(value)

    if result <= 0:
        raise ValueError("ttl_seconds must be greater than 0")

    return result


def _validate_payload(
    value: object,
) -> Payload:
    if not isinstance(
        value,
        dict,
    ):
        raise TypeError("payload must be a dictionary")

    payload = cast(
        dict[object, object],
        value,
    )

    if not all(isinstance(key, str) for key in payload):
        raise TypeError("payload keys must be strings")

    return cast(
        Payload,
        payload,
    )


def _validate_collector(
    value: object,
) -> Collector:
    if not callable(value):
        raise TypeError("collector must be callable")

    return cast(
        Collector,
        value,
    )


@dataclass(slots=True)
class StatusCache:
    ttl_seconds: float = 3.0
    payload: Payload | None = None
    collected_at: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(
        self,
    ) -> None:
        self.ttl_seconds = _validate_ttl(self.ttl_seconds)

        if self.payload is not None:
            self.payload = dict(_validate_payload(self.payload))

        self.collected_at = float(self.collected_at)

        if self.collected_at < 0:
            raise ValueError("collected_at cannot be negative")

    def is_fresh(
        self,
    ) -> bool:
        if self.payload is None:
            return False

        age = time.monotonic() - self.collected_at

        return 0 <= age < self.ttl_seconds

    async def get(
        self,
        collector: Collector,
    ) -> Payload:
        collector_value = _validate_collector(collector)

        if self.is_fresh():
            assert self.payload is not None
            return dict(self.payload)

        async with self.lock:
            if self.is_fresh():
                assert self.payload is not None
                return dict(self.payload)

            collected = await asyncio.to_thread(collector_value)
            payload = dict(_validate_payload(collected))

            self.payload = payload
            self.collected_at = time.monotonic()

            return dict(payload)

    def clear(
        self,
    ) -> None:
        self.payload = None
        self.collected_at = 0.0
