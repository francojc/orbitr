"""Unit tests for orbitr.core.cache."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from orbitr.core.cache import _SCHEMA_VERSION, Cache

# ---------------------------------------------------------------------------
# Fixture: isolated in-memory-style cache using tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture()
def cache(tmp_path: Path) -> Cache:
    c = Cache(db_path=tmp_path / "test.db")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Basic get / set
# ---------------------------------------------------------------------------


class TestGetSet:
    def test_set_and_get_returns_value(self, cache: Cache):
        cache.set("key1", {"data": [1, 2, 3]}, "search")
        result = cache.get("key1", "search")
        assert result == {"data": [1, 2, 3]}

    def test_get_missing_returns_none(self, cache: Cache):
        assert cache.get("nonexistent", "search") is None

    def test_get_wrong_tier_returns_none(self, cache: Cache):
        cache.set("key1", "value", "search")
        assert cache.get("key1", "paper") is None

    def test_set_overwrites_existing(self, cache: Cache):
        cache.set("key1", "old", "search")
        cache.set("key1", "new", "search")
        assert cache.get("key1", "search") == "new"

    def test_different_tiers_independent(self, cache: Cache):
        cache.set("key", "search-value", "search")
        cache.set("key", "paper-value", "paper")
        assert cache.get("key", "search") == "search-value"
        assert cache.get("key", "paper") == "paper-value"

    def test_values_json_roundtrip(self, cache: Cache):
        value = {"papers": [{"title": "Test", "year": 2021}], "count": 1}
        cache.set("complex", value, "paper")
        assert cache.get("complex", "paper") == value


# ---------------------------------------------------------------------------
# TTL / expiry
# ---------------------------------------------------------------------------


class TestExpiry:
    def test_expired_entry_returns_none(self, tmp_path: Path):
        """Set an entry with a 0-second TTL manually via sqlite, then get it."""

        cache = Cache(db_path=tmp_path / "ttl.db")
        # Directly insert an already-expired row
        conn = cache._connection()
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, tier, value, expires_at) VALUES (?, ?, ?, ?)",
            ("expired_key", "search", '"expired_value"', time.time() - 1),
        )
        conn.commit()
        assert cache.get("expired_key", "search") is None
        cache.close()

    def test_fresh_entry_not_expired(self, cache: Cache):
        cache.set("fresh", "value", "citations")
        assert cache.get("fresh", "citations") == "value"


# ---------------------------------------------------------------------------
# clean()
# ---------------------------------------------------------------------------


class TestClean:
    def test_clean_removes_expired(self, tmp_path: Path):
        cache = Cache(db_path=tmp_path / "clean.db")
        conn = cache._connection()
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, tier, value, expires_at) VALUES (?, ?, ?, ?)",
            ("old", "search", '"x"', time.time() - 1),
        )
        conn.commit()
        cache.set("fresh", "y", "search")

        deleted = cache.clean("search")
        assert deleted == 1
        assert cache.get("old", "search") is None
        assert cache.get("fresh", "search") == "y"
        cache.close()

    def test_clean_all_tiers(self, tmp_path: Path):
        cache = Cache(db_path=tmp_path / "cleanall.db")
        conn = cache._connection()
        for tier in ("search", "paper", "citations"):
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, tier, value, expires_at) VALUES (?, ?, ?, ?)",
                (f"old-{tier}", tier, '"x"', time.time() - 1),
            )
        conn.commit()
        deleted = cache.clean("all")
        assert deleted == 3
        cache.close()

    def test_clean_preserves_fresh(self, cache: Cache):
        cache.set("alive", "value", "paper")
        deleted = cache.clean("paper")
        assert deleted == 0
        assert cache.get("alive", "paper") == "value"


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


class TestClear:
    def test_clear_specific_tier(self, cache: Cache):
        cache.set("a", "1", "search")
        cache.set("b", "2", "paper")
        deleted = cache.clear("search")
        assert deleted == 1
        assert cache.get("a", "search") is None
        assert cache.get("b", "paper") == "2"

    def test_clear_all(self, cache: Cache):
        cache.set("a", "1", "search")
        cache.set("b", "2", "paper")
        cache.set("c", "3", "citations")
        deleted = cache.clear("all")
        assert deleted == 3
        stats = cache.stats()
        assert stats.total_entries == 0

    def test_clear_empty_returns_zero(self, cache: Cache):
        assert cache.clear("all") == 0


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------


class TestStats:
    def test_empty_stats(self, cache: Cache):
        stats = cache.stats()
        assert stats.total_entries == 0
        assert stats.entries_by_tier == {}

    def test_stats_counts_by_tier(self, cache: Cache):
        cache.set("a", 1, "search")
        cache.set("b", 2, "search")
        cache.set("c", 3, "paper")
        stats = cache.stats()
        assert stats.total_entries == 3
        assert stats.entries_by_tier["search"] == 2
        assert stats.entries_by_tier["paper"] == 1

    def test_stats_includes_db_path(self, cache: Cache, tmp_path: Path):
        stats = cache.stats()
        assert stats.db_path.parent == tmp_path

    def test_stats_size_bytes_positive_after_write(self, cache: Cache):
        cache.set("key", "value", "search")
        stats = cache.stats()
        assert stats.size_bytes > 0


# ---------------------------------------------------------------------------
# Schema versioning
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_fresh_db_gets_correct_version(self, tmp_path: Path):
        cache = Cache(db_path=tmp_path / "schema.db")
        conn = cache._connection()
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        assert row is not None
        assert int(row[0]) == _SCHEMA_VERSION
        cache.close()

    def test_version_mismatch_wipes_cache(self, tmp_path: Path):
        db = tmp_path / "mismatch.db"
        # Seed with a wrong schema version and some data
        cache = Cache(db_path=db)
        cache.set("key", "value", "search")
        conn = cache._connection()
        conn.execute("UPDATE meta SET value = '999' WHERE key = 'schema_version'")
        conn.commit()
        cache.close()

        # Re-open — should wipe the cache table
        cache2 = Cache(db_path=db)
        assert cache2.get("key", "search") is None
        cache2.close()
