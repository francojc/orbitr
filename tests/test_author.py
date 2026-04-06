"""Integration tests for orbitr author command."""

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


def _paper(title: str = "Bengio Paper", n: int = 0) -> Paper:
    return Paper(
        id=f"ss:auth{n}",
        title=title,
        authors=[Author(name="Yoshua Bengio")],
        abstract="Deep learning paper.",
        published_date=datetime(2015, 6, 1, tzinfo=timezone.utc),
        url="https://semanticscholar.org/paper/auth",
        source="semantic_scholar",
        citation_count=10000,
    )


def _invoke(*args: str, config: Config | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# Normal output
# ---------------------------------------------------------------------------


class TestAuthorOutput:
    def test_returns_papers(self):
        papers = [_paper(f"Paper {i}", i) for i in range(5)]
        with patch(
            "orbitr.commands.author.SemanticScholarClient.search_authors",
            new_callable=AsyncMock,
        ) as mock_sa:
            mock_sa.return_value = papers
            result = _invoke("author", "Yoshua Bengio")
        assert result.exit_code == 0
        mock_sa.assert_awaited_once()

    def test_author_name_passed_to_client(self):
        with patch(
            "orbitr.commands.author.SemanticScholarClient.search_authors",
            new_callable=AsyncMock,
        ) as mock_sa:
            mock_sa.return_value = [_paper()]
            _invoke("author", "Yoshua Bengio")
        args, _ = mock_sa.call_args
        assert args[0] == "Yoshua Bengio"

    def test_limit_passed_to_client(self):
        with patch(
            "orbitr.commands.author.SemanticScholarClient.search_authors",
            new_callable=AsyncMock,
        ) as mock_sa:
            mock_sa.return_value = [_paper()]
            _invoke("author", "LeCun", "--limit", "20")
        _, kwargs = mock_sa.call_args
        assert kwargs["limit"] == 20

    def test_json_format(self):
        with patch(
            "orbitr.commands.author.SemanticScholarClient.search_authors",
            new_callable=AsyncMock,
        ) as mock_sa:
            mock_sa.return_value = [_paper(title="LeCun Vision Paper")]
            result = _invoke("author", "LeCun", "--format", "json")
        assert result.exit_code == 0
        obj = json.loads(result.output.strip())
        assert obj["title"] == "LeCun Vision Paper"

    def test_title_in_output(self):
        with patch(
            "orbitr.commands.author.SemanticScholarClient.search_authors",
            new_callable=AsyncMock,
        ) as mock_sa:
            mock_sa.return_value = [_paper(title="Unique Title ABC")]
            result = _invoke("author", "Bengio")
        assert "Unique Title ABC" in result.output


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestAuthorErrors:
    def test_no_results_exits_4(self):
        with patch(
            "orbitr.commands.author.SemanticScholarClient.search_authors",
            new_callable=AsyncMock,
        ) as mock_sa:
            mock_sa.return_value = []
            result = _invoke("author", "Unknown Author XYZ")
        assert result.exit_code == 4

    def test_source_error_exits_1(self):
        with patch(
            "orbitr.commands.author.SemanticScholarClient.search_authors",
            new_callable=AsyncMock,
        ) as mock_sa:
            mock_sa.side_effect = SourceError("No author found.")
            result = _invoke("author", "Unknown")
        assert result.exit_code == 1

    def test_invalid_format_exits_2(self):
        result = _invoke("author", "Bengio", "--format", "xml")
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------


class TestAuthorCache:
    def test_cache_hit_skips_client(self):
        p = _paper()
        mock_cache = MagicMock()
        mock_cache.get.return_value = [json.loads(p.model_dump_json())]
        with (
            patch("orbitr.commands.author.Cache", return_value=mock_cache),
            patch(
                "orbitr.commands.author.SemanticScholarClient.search_authors",
                new_callable=AsyncMock,
            ) as mock_sa,
        ):
            result = _invoke("author", "Bengio", config=_test_config(no_cache=False))
        assert result.exit_code == 0
        mock_sa.assert_not_awaited()
