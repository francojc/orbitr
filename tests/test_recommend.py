"""Integration tests for orbitr recommend command."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.config import Config, Credentials
from orbitr.core.models import Author, Paper
from orbitr.exceptions import SourceError

runner = CliRunner()

_CREDS = Credentials()


def _test_config(**overrides) -> Config:
    base = Config(format="table", no_cache=True, credentials=_CREDS)
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _paper(title: str = "Recommended Paper", n: int = 0) -> Paper:
    return Paper(
        id=f"ss:rec{n}",
        title=title,
        authors=[Author(name="Alice Researcher")],
        abstract="A recommended paper abstract.",
        published_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
        url="https://semanticscholar.org/paper/rec",
        source="semantic_scholar",
        citation_count=50,
    )


def _invoke(*args: str, config: Config | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# Normal output
# ---------------------------------------------------------------------------


class TestRecommendOutput:
    def test_returns_papers(self):
        papers = [_paper(f"Paper {i}", i) for i in range(3)]
        with patch(
            "orbitr.commands.recommend.SemanticScholarClient.get_recommendations",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_rec.return_value = papers
            result = _invoke("recommend", "1706.03762")
        assert result.exit_code == 0
        mock_rec.assert_awaited_once()

    def test_uses_arxiv_prefix_for_arxiv_id(self):
        with patch(
            "orbitr.commands.recommend.SemanticScholarClient.get_recommendations",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_rec.return_value = [_paper()]
            _invoke("recommend", "1706.03762")
        args, _ = mock_rec.call_args
        assert args[0] == "ARXIV:1706.03762"

    def test_json_format(self):
        with patch(
            "orbitr.commands.recommend.SemanticScholarClient.get_recommendations",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_rec.return_value = [_paper(title="JSON Paper")]
            result = _invoke("recommend", "1706.03762", "--format", "json")
        assert result.exit_code == 0
        obj = json.loads(result.output.strip())
        assert obj["title"] == "JSON Paper"

    def test_limit_passed_to_client(self):
        with patch(
            "orbitr.commands.recommend.SemanticScholarClient.get_recommendations",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_rec.return_value = [_paper()]
            _invoke("recommend", "1706.03762", "--limit", "5")
        _, kwargs = mock_rec.call_args
        assert kwargs["limit"] == 5


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestRecommendErrors:
    def test_no_results_exits_4(self):
        with patch(
            "orbitr.commands.recommend.SemanticScholarClient.get_recommendations",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_rec.return_value = []
            result = _invoke("recommend", "1706.03762")
        assert result.exit_code == 4

    def test_source_error_exits_1(self):
        with patch(
            "orbitr.commands.recommend.SemanticScholarClient.get_recommendations",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_rec.side_effect = SourceError("API error.")
            result = _invoke("recommend", "1706.03762")
        assert result.exit_code == 1

    def test_invalid_format_exits_2(self):
        result = _invoke("recommend", "1706.03762", "--format", "csv")
        assert result.exit_code == 2

    def test_invalid_method_exits_2(self):
        result = _invoke("recommend", "1706.03762", "--method", "random")
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------


class TestRecommendCache:
    def test_cache_hit_skips_client(self):
        p = _paper()
        mock_cache = MagicMock()
        mock_cache.get.return_value = [json.loads(p.model_dump_json())]
        with (
            patch("orbitr.commands.recommend.Cache", return_value=mock_cache),
            patch(
                "orbitr.commands.recommend.SemanticScholarClient.get_recommendations",
                new_callable=AsyncMock,
            ) as mock_rec,
        ):
            result = _invoke(
                "recommend", "1706.03762", config=_test_config(no_cache=False)
            )
        assert result.exit_code == 0
        mock_rec.assert_not_awaited()
