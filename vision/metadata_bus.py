import threading
from typing import Dict, List, Optional

from betabox_car.vision.metadata import Metadata


class MetadataBus:
    """
    Stores and publishes metadata produced by Vision components.

    Detectors publish metadata to the bus. Streamers, APIs, and future
    user interfaces can read metadata without depending on detector
    internals.
    """

    def __init__(self) -> None:
        self._latest_by_source: Dict[str, Metadata] = {}
        self._history: List[Metadata] = []
        self._lock = threading.Lock()

    def publish(self, metadata: Metadata) -> None:
        with self._lock:
            self._latest_by_source[metadata.source] = metadata
            self._history.append(metadata)

    def latest(self, source: Optional[str] = None) -> Optional[Metadata]:
        with self._lock:
            if source is not None:
                return self._latest_by_source.get(source)

            if not self._history:
                return None

            return self._history[-1]

    def all_latest(self) -> Dict[str, Metadata]:
        with self._lock:
            return dict(self._latest_by_source)

    def history(self, limit: Optional[int] = None) -> List[Metadata]:
        with self._lock:
            if limit is None:
                return list(self._history)

            return list(self._history[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._latest_by_source.clear()
            self._history.clear()
