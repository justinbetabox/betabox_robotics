import threading
from collections import deque

from betabox_robotics.vision.metadata import Metadata


class MetadataBus:
    """
    Thread-safe store for metadata produced by Vision components.

    Detectors and other producers publish metadata to the bus. Streamers,
    APIs, overlays, and user interfaces can then consume that metadata
    without depending directly on producer implementations.

    The bus retains the latest item from each source and a bounded history of
    recently published metadata.
    """

    def __init__(
        self,
        *,
        max_history: int = 500,
    ) -> None:
        if isinstance(max_history, bool) or not isinstance(
            max_history,
            int,
        ):
            raise TypeError("max_history must be an integer")

        if max_history <= 0:
            raise ValueError("max_history must be greater than zero")

        self._latest_by_source: dict[str, Metadata] = {}
        self._history: deque[Metadata] = deque(maxlen=max_history)
        self._lock = threading.Lock()

    def publish(
        self,
        metadata: Metadata,
    ) -> None:
        """
        Publish metadata and make it the latest item for its source.
        """
        if not isinstance(metadata, Metadata):
            raise TypeError("metadata must be a Metadata instance")

        with self._lock:
            self._latest_by_source[metadata.source] = metadata
            self._history.append(metadata)

    def latest(
        self,
        source: str | None = None,
    ) -> Metadata | None:
        """
        Return the latest published metadata.

        When source is provided, return the latest metadata from that source.
        Otherwise, return the most recently published metadata from any
        source.
        """
        if source is not None and not isinstance(
            source,
            str,
        ):
            raise TypeError("source must be a string")

        with self._lock:
            if source is not None:
                return self._latest_by_source.get(source)

            return self._history[-1] if self._history else None

    def all_latest(
        self,
    ) -> dict[str, Metadata]:
        """
        Return the latest metadata from every known source.
        """
        with self._lock:
            return dict(self._latest_by_source)

    def history(
        self,
        limit: int | None = None,
    ) -> tuple[Metadata, ...]:
        """
        Return metadata history in oldest-to-newest order.

        When limit is supplied, return at most that many of the newest items.
        """
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(
                limit,
                int,
            ):
                raise TypeError("limit must be an integer")

            if limit < 0:
                raise ValueError("limit must be zero or greater")

        with self._lock:
            if limit is None:
                return tuple(self._history)

            if limit == 0:
                return ()

            return tuple(list(self._history)[-limit:])

    def clear(self) -> None:
        """
        Remove all current and historical metadata.
        """
        with self._lock:
            self._latest_by_source.clear()
            self._history.clear()
