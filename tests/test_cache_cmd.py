"""Integration tests for orbitr cache subcommands.

Strategy
--------
- Use Typer's ``CliRunner`` against the full ``app`` object.
- Patch ``orbitr.config.load_config`` to inject a deterministic ``Config``.
- Patch ``orbitr.commands.cache.Cache`` to avoid touching the filesystem.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.config import Config, Credentials
from orbitr.core.cache import CacheStats

runner = CliRunner()

_CREDS = Credentials()


def _test_config(**overrides) -> Config:
    base = Config(
        format="table",
        no_cache=True,
        credentials=_CREDS,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _mock_stats(
    total: int = 5,
    by_tier: dict | None = None,
    size: int = 4096,
) -> CacheStats:
    return CacheStats(
        total_entries=total,
        entries_by_tier=by_tier or {"search": 3, "paper": 1, "citations": 1},
        size_bytes=size,
        db_path=Path("/tmp/cache.db"),
    )


def _invoke(*args: str, config: Config | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# orbitr cache stats
# ---------------------------------------------------------------------------


class TestCacheStats:
    def test_stats_shows_tier_counts(self):
        mock_cache = MagicMock()
        mock_cache.stats.return_value = _mock_stats()
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "stats")
        assert result.exit_code == 0
        assert "search" in result.output
        assert "paper" in result.output
        assert "citations" in result.output

    def test_stats_shows_total(self):
        mock_cache = MagicMock()
        mock_cache.stats.return_value = _mock_stats(total=12)
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "stats")
        assert result.exit_code == 0
        assert "12" in result.output

    def test_stats_shows_db_path(self):
        mock_cache = MagicMock()
        mock_cache.stats.return_value = _mock_stats()
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "stats")
        assert result.exit_code == 0
        assert "/tmp/cache.db" in result.output

    def test_stats_empty_cache(self):
        mock_cache = MagicMock()
        mock_cache.stats.return_value = _mock_stats(total=0, by_tier={})
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "stats")
        assert result.exit_code == 0
        assert "0" in result.output


# ---------------------------------------------------------------------------
# orbitr cache clean
# ---------------------------------------------------------------------------


class TestCacheClean:
    def test_clean_all_default(self):
        mock_cache = MagicMock()
        mock_cache.clean.return_value = 7
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "clean")
        assert result.exit_code == 0
        assert "7" in result.output
        mock_cache.clean.assert_called_once_with("all")

    def test_clean_specific_tier(self):
        mock_cache = MagicMock()
        mock_cache.clean.return_value = 3
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "clean", "--tier", "search")
        assert result.exit_code == 0
        assert "3" in result.output
        mock_cache.clean.assert_called_once_with("search")

    def test_clean_zero_removed(self):
        mock_cache = MagicMock()
        mock_cache.clean.return_value = 0
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "clean")
        assert result.exit_code == 0
        assert "0" in result.output

    def test_clean_invalid_tier(self):
        result = _invoke("cache", "clean", "--tier", "invalid")
        assert result.exit_code == 2

    def test_clean_singular_noun(self):
        mock_cache = MagicMock()
        mock_cache.clean.return_value = 1
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "clean")
        assert result.exit_code == 0
        assert "entry" in result.output


# ---------------------------------------------------------------------------
# orbitr cache clear
# ---------------------------------------------------------------------------


class TestCacheClear:
    def test_clear_with_yes_flag(self):
        mock_cache = MagicMock()
        mock_cache.clear.return_value = 10
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "clear", "--yes")
        assert result.exit_code == 0
        assert "10" in result.output
        mock_cache.clear.assert_called_once_with("all")

    def test_clear_specific_tier_with_yes(self):
        mock_cache = MagicMock()
        mock_cache.clear.return_value = 4
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "clear", "--tier", "paper", "--yes")
        assert result.exit_code == 0
        assert "4" in result.output
        mock_cache.clear.assert_called_once_with("paper")

    def test_clear_invalid_tier(self):
        result = _invoke("cache", "clear", "--tier", "bogus", "--yes")
        assert result.exit_code == 2

    def test_clear_confirm_abort(self):
        mock_cache = MagicMock()
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            # CliRunner feeds empty input — typer.confirm raises Abort
            runner.invoke(
                app,
                ["cache", "clear"],
                input="\n",
                catch_exceptions=False,
            )
        # Aborted — nothing cleared
        mock_cache.clear.assert_not_called()

    def test_clear_confirm_yes_via_prompt(self):
        mock_cache = MagicMock()
        mock_cache.clear.return_value = 2
        with (
            patch("orbitr.config.load_config", return_value=_test_config()),
            patch("orbitr.commands.cache.Cache", return_value=mock_cache),
        ):
            result = runner.invoke(app, ["cache", "clear"], input="y\n")
        assert result.exit_code == 0
        mock_cache.clear.assert_called_once()

    def test_clear_zero_entries(self):
        mock_cache = MagicMock()
        mock_cache.clear.return_value = 0
        with patch("orbitr.commands.cache.Cache", return_value=mock_cache):
            result = _invoke("cache", "clear", "--yes")
        assert result.exit_code == 0
        assert "0" in result.output
