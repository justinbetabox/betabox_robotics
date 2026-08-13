from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class BackupItemData(TypedDict):
    source: str
    destination: str
    copied: bool
    message: str


class BackupReportData(TypedDict):
    name: str
    path: str
    created_at: str
    hostname: str
    sdk_version: str
    items: list[BackupItemData]


@dataclass(frozen=True, slots=True)
class BackupItem:
    source: str
    destination: str
    copied: bool
    message: str = ""

    def to_dict(self) -> BackupItemData:
        return {
            "source": self.source,
            "destination": self.destination,
            "copied": self.copied,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class BackupReport:
    name: str
    path: str
    created_at: str
    hostname: str
    sdk_version: str
    items: tuple[BackupItem, ...]

    def to_dict(self) -> BackupReportData:
        return {
            "name": self.name,
            "path": self.path,
            "created_at": self.created_at,
            "hostname": self.hostname,
            "sdk_version": self.sdk_version,
            "items": [item.to_dict() for item in self.items],
        }
