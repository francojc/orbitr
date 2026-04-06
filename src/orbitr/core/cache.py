"""SQLite-backed TTL cache with three independent tiers.

Tiers and default TTLs:
  search    — 1 hour   (query results change frequently)
  paper     — 24 hours (paper metadata is stable)
  citations — 6 hours  (citation counts update occasionally)

Cache location: ~/.cache/orbitr/cache.db (XDG Base Directory spec).
Schema is versioned; a version mismatch triggers a silent wipe and rebuild.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from orbitr.config import CACHE_DIR

logger = logging.getLogger(__name__)

T = TypeVar("T")
Tier = Literal["search", "paper", "citations"]

_SCHEMA_VERSION = 1
_TTL: dict[str, int] = {
    "search": 3600,  # 1 hour
    "paper": 86400,  # 24 hours
    "citations": 21600,  # 6 hours
}

_CREATE_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS cache (
    key        TEXT NOT NULL,
    tier       TEXT NOT NULL,
    value      TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY (key, tier)
)
"""

_CREATE_META_TABLE = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


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
        conn = self._connection()
        row = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ? AND tier = ?",
            (key, tier),
        ).fetchone()

        if row is None:
            return None

        value_json, expires_at = row
        if time.time() > expires_at:
            conn.execute("DELETE FROM cache WHERE key = ? AND tier = ?", (key, tier))
            conn.commit()
            return None

        return json.loads(value_json)

    def set(self, key: str, value: Any, tier: Tier) -> None:
        """Store a value in the cache under the given tier.

        Args:
            key: Cache key.
            value: JSON-serialisable value.
            tier: Cache tier (determines TTL).
        """
        expires_at = time.time() + _TTL[tier]
        conn = self._connection()
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, tier, value, expires_at) VALUES (?, ?, ?, ?)",
            (key, tier, json.dumps(value), expires_at),
        )
        conn.commit()

    def stats(self) -> CacheStats:
        """Return summary statistics for the cache.

        Returns:
            CacheStats with entry counts and disk usage.
        """
        conn = self._connection()
        total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        rows = conn.execute("SELECT tier, COUNT(*) FROM cache GROUP BY tier").fetchall()
        entries_by_tier = {tier: count for tier, count in rows}
        size_bytes = self._db_path.stat().st_size if self._db_path.exists() else 0
        return CacheStats(
            total_entries=total,
            entries_by_tier=entries_by_tier,
            size_bytes=size_bytes,
            db_path=self._db_path,
        )

    def clean(self, tier: Tier | Literal["all"] = "all") -> int:
        """Delete expired entries.

        Args:
            tier: Tier to clean, or 'all'.

        Returns:
            Number of entries deleted.
        """
        conn = self._connection()
        now = time.time()
        if tier == "all":
            cur = conn.execute("DELETE FROM cache WHERE expires_at < ?", (now,))
        else:
            cur = conn.execute(
                "DELETE FROM cache WHERE tier = ? AND expires_at < ?", (tier, now)
            )
        conn.commit()
        return cur.rowcount

    def clear(self, tier: Tier | Literal["all"] = "all") -> int:
        """Delete all entries regardless of TTL.

        Args:
            tier: Tier to clear, or 'all'.

        Returns:
            Number of entries deleted.
        """
        conn = self._connection()
        if tier == "all":
            cur = conn.execute("DELETE FROM cache")
        else:
            cur = conn.execute("DELETE FROM cache WHERE tier = ?", (tier,))
        conn.commit()
        return cur.rowcount

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connection(self) -> sqlite3.Connection:
        """Return the open database connection, reopening if closed."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
        return self._conn

    def _init_db(self) -> None:
        """Create tables and validate schema version. Wipe on mismatch."""
        conn = sqlite3.connect(str(self._db_path))
        self._conn = conn

        conn.execute(_CREATE_META_TABLE)
        conn.execute(_CREATE_CACHE_TABLE)

        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(_SCHEMA_VERSION),),
            )
            conn.commit()
        elif int(row[0]) != _SCHEMA_VERSION:
            logger.warning(
                "Cache schema version mismatch (expected %d, got %s). Wiping cache.",
                _SCHEMA_VERSION,
                row[0],
            )
            conn.execute("DROP TABLE IF EXISTS cache")
            conn.execute(_CREATE_CACHE_TABLE)
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(_SCHEMA_VERSION),),
            )
            conn.commit()
