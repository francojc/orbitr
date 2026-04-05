"""SQLite-backed TTL cache with three independent tiers.

Tiers and default TTLs:
  search    — 1 hour   (query results change frequently)
  paper     — 24 hours (paper metadata is stable)
  citations — 6 hours  (citation counts update occasionally)

Cache location: ~/.cache/lumen/cache.db (XDG Base Directory spec).
Schema is versioned; a version mismatch triggers a silent wipe and rebuild.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from lumen.config import CACHE_DIR

logger = logging.getLogger(__name__)

T = TypeVar("T")
Tier = Literal["search", "paper", "citations"]

_SCHEMA_VERSION = 1
_TTL: dict[Tier, int] = {
    "search": 3600,  # 1 hour
    "paper": 86400,  # 24 hours
    "citations": 21600,  # 6 hours
}


@dataclass
class CacheStats:
    """Summary statistics for the local cache."""

    total_entries: int
    entries_by_tier: dict[str, int]
    size_bytes: int
    db_path: Path


class Cache(Generic[T]):
    """SQLite-backed key-value store with per-tier TTL expiry."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or (CACHE_DIR / "cache.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(self, key: str, tier: Tier) -> Any | None:
        """Retrieve a cached value if it exists and has not expired.

        Args:
            key: Cache key (normalised query + source hash).
            tier: Cache tier to look up.

        Returns:
            Deserialised value, or None if missing/expired.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    def set(self, key: str, value: Any, tier: Tier) -> None:
        """Store a value in the cache under the given tier.

        Args:
            key: Cache key.
            value: JSON-serialisable value.
            tier: Cache tier (determines TTL).
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    def stats(self) -> CacheStats:
        """Return summary statistics for the cache.

        Returns:
            CacheStats with entry counts and disk usage.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    def clean(self, tier: Tier | Literal["all"] = "all") -> int:
        """Delete expired entries.

        Args:
            tier: Tier to clean, or "all".

        Returns:
            Number of entries deleted.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    def clear(self, tier: Tier | Literal["all"] = "all") -> int:
        """Delete all entries regardless of TTL.

        Args:
            tier: Tier to clear, or "all".

        Returns:
            Number of entries deleted.
        """
        # TODO: implement in Phase 2
        raise NotImplementedError

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create tables and validate schema version. Wipe on mismatch."""
        # TODO: implement in Phase 2
        raise NotImplementedError
