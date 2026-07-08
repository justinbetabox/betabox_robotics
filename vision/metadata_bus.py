import threading
from collections import deque
from collections.abc import Sequence

from betabox_robotics.vision.metadata import Metadata


class MetadataBus:
    """
    Stores and publishes metadata produced by Vision components.

    Detectors publish metadata to the bus. Streamers, APIs, and future
    user interfaces can read metadata without depending on detector
    internals.
    """

    def __init__(self, *, max_history: int = 500) -> None:
        self._latest_by_source: dict[str, Metadata] = {}
        self._history: deque[Metadata] = deque(maxlen=max_history)
        self._lock = threading.Lock()

    def publish(self, metadata: Metadata) -> None:
        with self._lock:
            self._latest_by_source[metadata.source] = metadata
            self._history.append(metadata)

    def latest(self, source: str | None = None) -> Metadata | None:
        with self._lock:
            if source is not None:
                return self._latest_by_source.get(source)

            if not self._history:
                return None

            return self._history[-1]

    def all_latest(self) -> dict[str, Metadata]:
        with self._lock:
            return dict(self._latest_by_source)

    def history(self, limit: int | None = None) -> Sequence[Metadata]:
        with self._lock:
            items = list(self._history)

        if limit is None:
            return items

        return items[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._latest_by_source.clear()
            self._history.clear()
