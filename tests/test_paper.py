"""Integration tests for orbitr paper and orbitr cite commands.

Strategy
--------
- Use Typer's ``CliRunner`` against the full ``app`` object.
- Patch ``orbitr.config.load_config`` to inject a deterministic ``Config``
  with ``no_cache=True`` so most tests bypass the cache entirely.
- Patch ``ArxivClient.get_by_id`` or ``SemanticScholarClient.get_by_id`` /
  ``get_citations`` at the method level with ``AsyncMock`` — no live network.
- Cache-hit tests patch ``orbitr.commands.paper.Cache`` directly.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.commands.paper import _detect_id_type, _normalize_for_ss
from orbitr.config import Config, Credentials
from orbitr.core.models import Author, Paper
from orbitr.exceptions import SourceError

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


def _paper(
    title: str = "Attention Is All You Need",
    source: str = "arxiv",
    arxiv_id: str | None = "1706.03762",
    doi: str | None = None,
) -> Paper:
    return Paper(
        id=f"{source}:1706.03762",
        title=title,
        authors=[Author(name="Vaswani et al.")],
        abstract="Transformer architecture paper.",
        published_date=datetime(2017, 6, 12, tzinfo=timezone.utc),
        url="https://arxiv.org/abs/1706.03762",
        source=source,
        citation_count=100_000,
        arxiv_id=arxiv_id,
        doi=doi,
    )


def _invoke(*args: str, config: Config | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# Unit tests: _detect_id_type and _normalize_for_ss
# ---------------------------------------------------------------------------


class TestDetectIdType:
    def test_bare_arxiv_new_format(self):
        assert _detect_id_type("1706.03762") == "arxiv"

    def test_arxiv_with_version(self):
        assert _detect_id_type("1706.03762v2") == "arxiv"

    def test_arxiv_old_format(self):
        assert _detect_id_type("cs/0301027") == "arxiv"

    def test_arxiv_with_prefix(self):
        assert _detect_id_type("arxiv:1706.03762") == "arxiv"

    def test_arxiv_url(self):
        assert _detect_id_type("https://arxiv.org/abs/1706.03762") == "arxiv"

    def test_doi_bare(self):
        assert _detect_id_type("10.18653/v1/2020.acl-main.196") == "doi"

    def test_doi_url(self):
        assert _detect_id_type("https://doi.org/10.18653/v1/P16-1162") == "doi"

    def test_doi_prefix(self):
        assert _detect_id_type("DOI:10.1145/3292500.3330701") == "doi"

    def test_ss_id(self):
        assert (
            _detect_id_type("204e3073870fae3d05bcbc2f6a8e263d9b72e776")
            == "semantic_scholar"
        )

    def test_unknown(self):
        assert _detect_id_type("some random string") == "unknown"


class TestNormalizeForSS:
    def test_arxiv_bare(self):
        assert _normalize_for_ss("1706.03762", "arxiv") == "ARXIV:1706.03762"

    def test_arxiv_strips_version(self):
        assert _normalize_for_ss("1706.03762v2", "arxiv") == "ARXIV:1706.03762"

    def test_arxiv_strips_url(self):
        result = _normalize_for_ss("https://arxiv.org/abs/1706.03762", "arxiv")
        assert result == "ARXIV:1706.03762"

    def test_doi_bare(self):
        result = _normalize_for_ss("10.18653/v1/P16-1162", "doi")
        assert result == "DOI:10.18653/v1/P16-1162"

    def test_doi_strips_url(self):
        result = _normalize_for_ss("https://doi.org/10.18653/v1/P16-1162", "doi")
        assert result == "DOI:10.18653/v1/P16-1162"

    def test_ss_id_passthrough(self):
        ss_id = "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
        assert _normalize_for_ss(ss_id, "semantic_scholar") == ss_id

    def test_unknown_passthrough(self):
        assert _normalize_for_ss("anything", "unknown") == "anything"


# ---------------------------------------------------------------------------
# orbitr paper — arXiv ID
# ---------------------------------------------------------------------------


class TestPaperArxiv:
    def test_arxiv_id_calls_arxiv_client(self):
        p = _paper()
        with patch(
            "orbitr.commands.paper.ArxivClient.get_by_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = p
            result = _invoke("paper", "1706.03762")
        assert result.exit_code == 0
        mock_get.assert_awaited_once()

    def test_arxiv_id_output_contains_title(self):
        p = _paper(title="Unique Title XYZ")
        with patch(
            "orbitr.commands.paper.ArxivClient.get_by_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = p
            result = _invoke("paper", "1706.03762")
        assert "Unique Title XYZ" in result.output

    def test_arxiv_json_format(self):
        p = _paper()
        with patch(
            "orbitr.commands.paper.ArxivClient.get_by_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = p
            result = _invoke("paper", "1706.03762", "--format", "json")
        assert result.exit_code == 0
        obj = json.loads(result.output.strip())
        assert obj["title"] == "Attention Is All You Need"

    def test_arxiv_source_error_exits_1(self):
        with patch(
            "orbitr.commands.paper.ArxivClient.get_by_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = SourceError("Not found.")
            result = _invoke("paper", "9999.99999")
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# orbitr paper — DOI / Semantic Scholar ID
# ---------------------------------------------------------------------------


class TestPaperSS:
    def test_doi_calls_ss_client(self):
        p = _paper(source="semantic_scholar", arxiv_id=None, doi="10.18653/v1/P16-1162")
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_by_id",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = p
            result = _invoke("paper", "10.18653/v1/P16-1162")
        assert result.exit_code == 0
        # SS normalises DOI with prefix
        mock_get.assert_awaited_once_with("DOI:10.18653/v1/P16-1162")

    def test_ss_id_calls_ss_client(self):
        ss_id = "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
        p = _paper(source="semantic_scholar", arxiv_id=None)
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_by_id",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = p
            result = _invoke("paper", ss_id)
        assert result.exit_code == 0
        mock_get.assert_awaited_once_with(ss_id)

    def test_ss_source_error_exits_1(self):
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_by_id",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.side_effect = SourceError("Not found.")
            result = _invoke("paper", "10.9999/nonexistent")
        assert result.exit_code == 1

    def test_invalid_format_exits_2(self):
        result = _invoke("paper", "1706.03762", "--format", "xml")
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# orbitr paper — cache hit
# ---------------------------------------------------------------------------


class TestPaperCacheHit:
    def test_cache_hit_skips_client(self):
        p = _paper()
        mock_cache = MagicMock()
        mock_cache.get.return_value = json.loads(p.model_dump_json())
        with (
            patch("orbitr.commands.paper.Cache", return_value=mock_cache),
            patch(
                "orbitr.commands.paper.ArxivClient.get_by_id", new_callable=AsyncMock
            ) as mock_get,
        ):
            result = _invoke("paper", "1706.03762", config=_test_config(no_cache=False))
        assert result.exit_code == 0
        mock_get.assert_not_awaited()


# ---------------------------------------------------------------------------
# orbitr cite
# ---------------------------------------------------------------------------


class TestCite:
    def test_cite_returns_papers(self):
        papers = [_paper(title=f"Citing Paper {i}") for i in range(3)]
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_citations",
            new_callable=AsyncMock,
        ) as mock_cit:
            mock_cit.return_value = papers
            result = _invoke("cite", "1706.03762")
        assert result.exit_code == 0
        mock_cit.assert_awaited_once()

    def test_cite_passes_arxiv_prefix(self):
        papers = [_paper()]
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_citations",
            new_callable=AsyncMock,
        ) as mock_cit:
            mock_cit.return_value = papers
            _invoke("cite", "1706.03762")
        args, _ = mock_cit.call_args
        # First positional arg is the SS-normalised ID
        assert args[0] == "ARXIV:1706.03762"

    def test_cite_limit_applied(self):
        papers = [_paper(title=f"Paper {i}") for i in range(20)]
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_citations",
            new_callable=AsyncMock,
        ) as mock_cit:
            mock_cit.return_value = papers[:5]
            result = _invoke("cite", "1706.03762", "--limit", "5")
        assert result.exit_code == 0
        _, kwargs = mock_cit.call_args
        assert kwargs["limit"] == 5

    def test_cite_json_format(self):
        papers = [_paper()]
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_citations",
            new_callable=AsyncMock,
        ) as mock_cit:
            mock_cit.return_value = papers
            result = _invoke("cite", "1706.03762", "--format", "json")
        assert result.exit_code == 0
        obj = json.loads(result.output.strip())
        assert obj["title"] == "Attention Is All You Need"

    def test_cite_no_results_exits_4(self):
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_citations",
            new_callable=AsyncMock,
        ) as mock_cit:
            mock_cit.return_value = []
            result = _invoke("cite", "1706.03762")
        assert result.exit_code == 4

    def test_cite_source_error_exits_1(self):
        with patch(
            "orbitr.commands.paper.SemanticScholarClient.get_citations",
            new_callable=AsyncMock,
        ) as mock_cit:
            mock_cit.side_effect = SourceError("API error.")
            result = _invoke("cite", "1706.03762")
        assert result.exit_code == 1

    def test_cite_invalid_format_exits_2(self):
        result = _invoke("cite", "1706.03762", "--format", "csv")
        assert result.exit_code == 2

    def test_cite_cache_hit_skips_client(self):
        p = _paper()
        mock_cache = MagicMock()
        mock_cache.get.return_value = [json.loads(p.model_dump_json())]
        with (
            patch("orbitr.commands.paper.Cache", return_value=mock_cache),
            patch(
                "orbitr.commands.paper.SemanticScholarClient.get_citations",
                new_callable=AsyncMock,
            ) as mock_cit,
        ):
            result = _invoke("cite", "1706.03762", config=_test_config(no_cache=False))
        assert result.exit_code == 0
        mock_cit.assert_not_awaited()
