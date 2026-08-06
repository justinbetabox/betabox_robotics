from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BackupItem:
    source: str
    destination: str
    copied: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BackupReport:
    name: str
    path: str
    created_at: str
    hostname: str
    sdk_version: str
    items: tuple[BackupItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "created_at": self.created_at,
            "hostname": self.hostname,
            "sdk_version": self.sdk_version,
            "items": [item.to_dict() for item in self.items],
        }
