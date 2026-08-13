from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class RestoreItemData(TypedDict):
    source: str
    destination: str
    restored: bool
    message: str


@dataclass(frozen=True, slots=True)
class RestoreItem:
    source: str
    destination: str
    restored: bool
    message: str = ""

    def to_dict(
        self,
    ) -> RestoreItemData:
        return {
            "source": self.source,
            "destination": self.destination,
            "restored": self.restored,
            "message": self.message,
        }
