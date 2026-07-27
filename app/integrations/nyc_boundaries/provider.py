import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings, get_settings
from app.integrations.nyc_boundaries.cache import (
    NYCBoundaryCache,
)
from app.integrations.nyc_boundaries.client import (
    NYCBoundaryClient,
)
from app.integrations.nyc_boundaries.index import (
    NYCBoundaryIndex,
)

BoundaryIndexSource = Literal[
    "memory",
    "redis",
    "network",
]


@dataclass(frozen=True, slots=True)
class BoundaryIndexLoadResult:
    """A loaded boundary index and the layer it came from."""

    index: NYCBoundaryIndex
    source: BoundaryIndexSource


class NYCBoundaryIndexProvider:
    """Load and cache the NYC boundary spatial index."""

    def __init__(
        self,
        client: NYCBoundaryClient,
        cache: NYCBoundaryCache,
        settings: Settings | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.cache = cache
        self.settings = settings or get_settings()
        self.clock = clock

        self._index: NYCBoundaryIndex | None = None
        self._loaded_at: float | None = None
        self._lock = asyncio.Lock()

    def _memory_cache_is_fresh(self) -> bool:
        if self._index is None or self._loaded_at is None:
            return False

        elapsed_seconds = self.clock() - self._loaded_at

        return elapsed_seconds < (self.settings.nyc_boundary_cache_ttl_seconds)

    def _store_in_memory(
        self,
        index: NYCBoundaryIndex,
    ) -> None:
        self._index = index
        self._loaded_at = self.clock()

    async def get_index(
        self,
        *,
        force_refresh: bool = False,
    ) -> BoundaryIndexLoadResult:
        """Return an index from memory, Redis, or NYC Open Data."""

        if not force_refresh and self._memory_cache_is_fresh():
            assert self._index is not None

            return BoundaryIndexLoadResult(
                index=self._index,
                source="memory",
            )

        # Only one coroutine may rebuild the index at a time.
        async with self._lock:
            if not force_refresh and self._memory_cache_is_fresh():
                assert self._index is not None

                return BoundaryIndexLoadResult(
                    index=self._index,
                    source="memory",
                )

            if not force_refresh:
                cached_collection = await self.cache.get_feature_collection()

                if cached_collection is not None:
                    index = NYCBoundaryIndex(cached_collection.features)

                    self._store_in_memory(index)

                    return BoundaryIndexLoadResult(
                        index=index,
                        source="redis",
                    )

            feature_collection = await self.client.fetch_feature_collection()

            index = NYCBoundaryIndex(feature_collection.features)

            await self.cache.set_feature_collection(feature_collection)

            self._store_in_memory(index)

            return BoundaryIndexLoadResult(
                index=index,
                source="network",
            )

    def clear_memory_cache(self) -> None:
        """Remove only the current process's cached index."""

        self._index = None
        self._loaded_at = None
