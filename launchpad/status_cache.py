from __future__ import annotations

import time
from typing import Callable

from dataclasses import dataclass, field

import asyncio


Payload = dict[str, object]
Collector = Callable[[], Payload]


@dataclass
class StatusCache:
    ttl_seconds: float = 3.0
    payload: Payload | None = None
    collected_at: float = 0.0
    lock: asyncio.Lock = field(
        default_factory=asyncio.Lock
    )

    def is_fresh(self) -> bool:
        if self.payload is None:
            return False

        age = (
            time.monotonic()
            - self.collected_at
        )

        return age < self.ttl_seconds

    async def get(
        self,
        collector: Collector,
    ) -> Payload:
        if self.is_fresh():
            return self.payload or {}

        async with self.lock:
            if self.is_fresh():
                return self.payload or {}

            payload = await asyncio.to_thread(
                collector
            )

            self.payload = payload
            self.collected_at = (
                time.monotonic()
            )

            return payload

    def clear(self) -> None:
        self.payload = None
        self.collected_at = 0.0
