"""Integration tests for lumen search command.

Strategy
--------
- Use Typer's ``CliRunner`` against the full ``app`` object.
- Patch ``lumen.config.load_config`` to inject a deterministic ``Config``
  with ``no_cache=True`` so tests never read or write disk.
- Patch ``ArxivClient.search`` and ``SemanticScholarClient.search`` to
  return fixture-based ``SearchResult`` objects — no live network calls.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from lumen.cli import app
from lumen.config import Config, Credentials
from lumen.core.models import Author, Paper, SearchResult
from lumen.exceptions import SourceError

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_CREDS = Credentials(semantic_scholar_api_key="", zotero_user_id="", zotero_api_key="")


def _test_config(**overrides) -> Config:
    """Return a Config suitable for CLI tests (no cache, no credentials)."""
    base = Config(
        sources=["arxiv", "semantic_scholar"],
        max_results=10,
        format="table",
        no_cache=True,
        credentials=_CREDS,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _paper(
    title: str = "Test Paper",
    source: str = "arxiv",
    year: int = 2023,
    citations: int | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
) -> Paper:
    """Factory for minimal Paper instances."""
    return Paper(
        id=f"{source}-{title[:8].replace(' ', '_')}",
        title=title,
        authors=[Author(name="Jane Doe"), Author(name="John Smith")],
        abstract="Abstract text for testing purposes.",
        published_date=datetime(year, 6, 1, tzinfo=timezone.utc),
        url=f"https://example.com/{source}/{title[:8]}",
        source=source,
        citation_count=citations,
        doi=doi,
        arxiv_id=arxiv_id,
    )


def _result(
    papers: list[Paper], query: str = "test", sources: list[str] | None = None
) -> SearchResult:
    return SearchResult(
        papers=papers,
        total_count=len(papers),
        query=query,
        sources=sources or ["arxiv"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(*args: str, config: Config | None = None):
    """Invoke the CLI with patched load_config and return the result."""
    cfg = config or _test_config()
    with patch("lumen.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# 1. Basic search — table output
# ---------------------------------------------------------------------------


class TestSearchBasic:
    def test_table_output_contains_title(self):
        papers = [_paper("Attention Is All You Need", source="arxiv")]
        arxiv_mock = AsyncMock(return_value=_result(papers, sources=["arxiv"]))
        ss_mock = AsyncMock(return_value=_result([], sources=["semantic_scholar"]))

        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = arxiv_mock
            mock_ss_cls.return_value.search = ss_mock

            result = _invoke("search", "attention", "--no-cache")

        assert result.exit_code == 0, result.output
        # Rich table wraps long titles across rows; check both fragments.
        assert "Attention Is All You" in result.output
        assert "Need" in result.output

    def test_exits_zero_on_results(self):
        papers = [_paper("Transformers", source="arxiv")]
        arxiv_mock = AsyncMock(return_value=_result(papers, sources=["arxiv"]))
        ss_mock = AsyncMock(return_value=_result([], sources=["semantic_scholar"]))

        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = arxiv_mock
            mock_ss_cls.return_value.search = ss_mock

            result = _invoke("search", "transformers", "--no-cache")

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 2. Format flags
# ---------------------------------------------------------------------------


class TestSearchFormats:
    def _run_with_papers(self, papers: list[Paper], *extra_args: str):
        arxiv_mock = AsyncMock(return_value=_result(papers, sources=["arxiv"]))
        ss_mock = AsyncMock(return_value=_result([], sources=["semantic_scholar"]))
        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = arxiv_mock
            mock_ss_cls.return_value.search = ss_mock
            return _invoke("search", "test", "--no-cache", *extra_args)

    def test_format_json_is_ndjson(self):
        papers = [_paper("Paper A"), _paper("Paper B", source="semantic_scholar")]
        result = self._run_with_papers(papers, "--format", "json")
        assert result.exit_code == 0, result.output
        lines = [ln for ln in result.output.strip().splitlines() if ln.strip()]
        assert len(lines) >= 1
        obj = json.loads(lines[0])
        assert "title" in obj

    def test_format_list_shows_panel(self):
        papers = [_paper("Panel Paper")]
        result = self._run_with_papers(papers, "--format", "list")
        assert result.exit_code == 0
        assert "Panel Paper" in result.output

    def test_format_invalid_exits_2(self):
        result = _invoke("search", "test", "--format", "xml")
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# 3. --sources validation
# ---------------------------------------------------------------------------


class TestSearchSources:
    def test_single_source_arxiv(self):
        papers = [_paper("ArXiv Only")]
        arxiv_mock = AsyncMock(return_value=_result(papers, sources=["arxiv"]))
        with patch("lumen.commands.search.ArxivClient") as mock_ax_cls:
            mock_ax_cls.return_value.search = arxiv_mock
            result = _invoke("search", "test", "--no-cache", "--sources", "arxiv")

        assert result.exit_code == 0
        assert "ArXiv Only" in result.output

    def test_invalid_source_exits_2(self):
        result = _invoke("search", "test", "--sources", "google_scholar")
        assert result.exit_code == 2

    def test_mixed_valid_invalid_exits_2(self):
        result = _invoke("search", "test", "--sources", "arxiv,fakesource")
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# 4. --sort validation
# ---------------------------------------------------------------------------


class TestSearchSort:
    def test_invalid_sort_exits_2(self):
        result = _invoke("search", "test", "--sort", "magic")
        assert result.exit_code == 2

    def test_valid_sorts_accepted(self):
        papers = [_paper("Sorted Paper")]
        for criterion in ("relevance", "citations", "date", "impact", "combined"):
            arxiv_mock = AsyncMock(return_value=_result(papers, sources=["arxiv"]))
            ss_mock = AsyncMock(return_value=_result([], sources=["semantic_scholar"]))
            with (
                patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
                patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
            ):
                mock_ax_cls.return_value.search = arxiv_mock
                mock_ss_cls.return_value.search = ss_mock
                result = _invoke("search", "test", "--no-cache", "--sort", criterion)
            assert result.exit_code == 0, f"--sort {criterion} failed: {result.output}"


# ---------------------------------------------------------------------------
# 5. No results → exit 4
# ---------------------------------------------------------------------------


class TestSearchNoResults:
    def test_empty_results_exits_4(self):
        empty = AsyncMock(return_value=_result([], sources=["arxiv"]))
        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = empty
            mock_ss_cls.return_value.search = AsyncMock(
                return_value=_result([], sources=["semantic_scholar"])
            )
            result = _invoke("search", "zzz-no-results", "--no-cache")

        assert result.exit_code == 4


# ---------------------------------------------------------------------------
# 6. Source error → exit 1
# ---------------------------------------------------------------------------


class TestSearchSourceError:
    def test_all_sources_fail_exits_1(self):
        err_mock = AsyncMock(
            side_effect=SourceError("API down", suggestion="Try later.")
        )
        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = err_mock
            mock_ss_cls.return_value.search = err_mock
            result = _invoke("search", "test", "--no-cache")

        assert result.exit_code == 1

    def test_partial_source_failure_still_returns_results(self):
        """One source fails; results from the surviving source are returned."""
        good_papers = [_paper("Surviving Paper", source="arxiv")]
        arxiv_mock = AsyncMock(return_value=_result(good_papers, sources=["arxiv"]))
        ss_mock = AsyncMock(side_effect=SourceError("SS down", suggestion=""))

        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = arxiv_mock
            mock_ss_cls.return_value.search = ss_mock
            result = _invoke("search", "test", "--no-cache")

        assert result.exit_code == 0
        assert "Surviving Paper" in result.output


# ---------------------------------------------------------------------------
# 7. Deduplication across sources
# ---------------------------------------------------------------------------


class TestSearchDedup:
    def test_same_paper_from_two_sources_deduped(self):
        """A paper with the same DOI from both sources appears only once."""
        doi = "10.5555/test.001"
        arxiv_paper = _paper("Shared Paper", source="arxiv", doi=doi)
        ss_paper = _paper("Shared Paper", source="semantic_scholar", doi=doi)

        arxiv_mock = AsyncMock(
            return_value=_result([arxiv_paper], query="test", sources=["arxiv"])
        )
        ss_mock = AsyncMock(
            return_value=_result([ss_paper], query="test", sources=["semantic_scholar"])
        )

        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = arxiv_mock
            mock_ss_cls.return_value.search = ss_mock
            result = _invoke("search", "test", "--no-cache", "--format", "json")

        assert result.exit_code == 0, result.output
        lines = [ln for ln in result.output.strip().splitlines() if ln.strip()]
        titles = [json.loads(ln)["title"] for ln in lines]
        assert titles.count("Shared Paper") == 1, f"Expected 1 copy, got: {titles}"


# ---------------------------------------------------------------------------
# 8. --no-cache bypasses cache
# ---------------------------------------------------------------------------


class TestSearchCache:
    def test_no_cache_flag_calls_client(self):
        """With --no-cache, the client is always called (cache is not consulted)."""
        papers = [_paper("Cache Test")]
        arxiv_mock = AsyncMock(return_value=_result(papers, sources=["arxiv"]))
        ss_mock = AsyncMock(return_value=_result([], sources=["semantic_scholar"]))

        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = arxiv_mock
            mock_ss_cls.return_value.search = ss_mock
            result = _invoke("search", "cache test", "--no-cache")

        assert result.exit_code == 0
        arxiv_mock.assert_called_once()


# ---------------------------------------------------------------------------
# 9. Year-range filtering
# ---------------------------------------------------------------------------


class TestSearchYearFilter:
    def test_year_from_filters_old_papers(self):
        old = _paper("Old Paper", year=2010)
        recent = _paper("Recent Paper", year=2022)
        arxiv_mock = AsyncMock(return_value=_result([old, recent], sources=["arxiv"]))
        ss_mock = AsyncMock(return_value=_result([], sources=["semantic_scholar"]))

        with (
            patch("lumen.commands.search.ArxivClient") as mock_ax_cls,
            patch("lumen.commands.search.SemanticScholarClient") as mock_ss_cls,
        ):
            mock_ax_cls.return_value.search = arxiv_mock
            mock_ss_cls.return_value.search = ss_mock
            result = _invoke(
                "search", "test", "--no-cache", "--format", "json", "--from", "2020"
            )

        assert result.exit_code == 0
        lines = [ln for ln in result.output.strip().splitlines() if ln.strip()]
        titles = [json.loads(ln)["title"] for ln in lines]
        assert "Old Paper" not in titles
        assert "Recent Paper" in titles


# ---------------------------------------------------------------------------
# 10. Field filter helpers (unit-level, not CLI)
# ---------------------------------------------------------------------------


class TestQueryHelpers:
    def test_parse_query_extracts_title(self):
        from lumen.core.query import parse_query

        base, filters = parse_query('BERT title:"contextual embeddings"')
        assert base.strip() == "BERT"
        assert filters["title"] == "contextual embeddings"

    def test_parse_query_extracts_author(self):
        from lumen.core.query import parse_query

        base, filters = parse_query("transformers author:Vaswani")
        assert "transformers" in base
        assert filters["author"] == "Vaswani"

    def test_parse_query_no_filters(self):
        from lumen.core.query import parse_query

        base, filters = parse_query("neural machine translation")
        assert base == "neural machine translation"
        assert filters == {}

    def test_build_arxiv_query_with_filters(self):
        from lumen.core.query import build_arxiv_query

        q = build_arxiv_query("BERT", {"title": "contextual", "author": "Devlin"})
        assert "all:BERT" in q
        assert "ti:contextual" in q
        assert "au:Devlin" in q
        assert "AND" in q

    def test_build_ss_query_flattens_filters(self):
        from lumen.core.query import build_ss_query

        q = build_ss_query("BERT", {"title": "contextual", "author": "Devlin"})
        assert "BERT" in q
        assert "contextual" in q
        assert "Devlin" in q

    def test_cache_key_is_deterministic(self):
        from lumen.core.query import cache_key

        k1 = cache_key("arxiv", "all:BERT", 10, "relevance")
        k2 = cache_key("arxiv", "all:BERT", 10, "relevance")
        assert k1 == k2
        assert k1.startswith("search:arxiv:")

    def test_cache_key_differs_for_different_queries(self):
        from lumen.core.query import cache_key

        k1 = cache_key("arxiv", "all:BERT", 10, "relevance")
        k2 = cache_key("arxiv", "all:GPT", 10, "relevance")
        assert k1 != k2

    def test_in_year_range(self):
        from lumen.core.query import in_year_range

        assert in_year_range(2020, 2015, 2023)
        assert not in_year_range(2010, 2015, 2023)
        assert in_year_range(None, 2015, 2023)  # unknown year always passes
        assert in_year_range(2020, None, None)  # open bounds always pass

    def test_ss_year_param(self):
        from lumen.core.query import ss_year_param

        assert ss_year_param(2017, 2022) == "2017-2022"
        assert ss_year_param(2017, None) == "2017-"
        assert ss_year_param(None, 2022) == "-2022"
        assert ss_year_param(None, None) is None
