from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RestoreItem:
    source: str
    destination: str
    restored: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
