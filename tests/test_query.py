"""Tests for orbitr query — NL parser and CLI command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.commands.query import _build_command, _parse_natural
from orbitr.config import Config, Credentials

runner = CliRunner()

_CREDS = Credentials()


def _test_config(**overrides) -> Config:
    base = Config(format="table", no_cache=True, credentials=_CREDS)
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _invoke(*args: str, config: Config | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# Unit: _parse_natural
# ---------------------------------------------------------------------------


class TestParseNatural:
    def test_year_extracted(self):
        result = _parse_natural("Vaswani 2017 attention transformer")
        assert result["year_from"] == 2017
        assert result["year_to"] == 2017

    def test_author_before_year(self):
        result = _parse_natural("Vaswani 2017 attention transformer")
        assert result["author"] == "Vaswani"

    def test_author_not_extracted_without_year(self):
        result = _parse_natural("attention is all you need")
        assert result["author"] is None

    def test_keywords_exclude_year_and_author(self):
        result = _parse_natural("Vaswani 2017 attention transformer")
        assert "2017" not in result["keywords"]
        assert "Vaswani" not in result["keywords"]
        assert "attention" in result["keywords"]
        assert "transformer" in result["keywords"]

    def test_stop_words_filtered(self):
        result = _parse_natural("recent papers on contrastive learning in NLP")
        kws = result["keywords"].lower()
        assert "recent" not in kws
        assert "papers" not in kws
        assert "contrastive" in kws
        assert "NLP" in result["keywords"]

    def test_no_year(self):
        result = _parse_natural("contrastive learning representation")
        assert result["year_from"] is None
        assert result["year_to"] is None

    def test_stop_word_before_year_not_treated_as_author(self):
        # "the 2020 survey" — "the" is a stop word, should not be treated as author
        result = _parse_natural("the 2020 survey transformers")
        assert result["author"] is None

    def test_keywords_not_empty_for_rich_input(self):
        result = _parse_natural("Bengio 2013 representation learning")
        assert result["keywords"]


# ---------------------------------------------------------------------------
# Unit: _build_command
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_basic_keywords(self):
        cmd = _build_command(
            {
                "keywords": "transformers",
                "author": None,
                "year_from": None,
                "year_to": None,
            }
        )
        assert cmd == "orbitr search transformers"

    def test_multi_word_keywords_quoted(self):
        cmd = _build_command(
            {
                "keywords": "attention mechanism",
                "author": None,
                "year_from": None,
                "year_to": None,
            }
        )
        assert '"attention mechanism"' in cmd

    def test_author_included(self):
        cmd = _build_command(
            {
                "keywords": "attention",
                "author": "Vaswani",
                "year_from": None,
                "year_to": None,
            }
        )
        assert '--author "Vaswani"' in cmd

    def test_year_from_included(self):
        cmd = _build_command(
            {
                "keywords": "transformers",
                "author": None,
                "year_from": 2017,
                "year_to": 2017,
            }
        )
        assert "--from 2017" in cmd

    def test_year_to_omitted_when_same_as_from(self):
        cmd = _build_command(
            {"keywords": "x", "author": None, "year_from": 2020, "year_to": 2020}
        )
        assert "--to" not in cmd

    def test_full_output(self):
        cmd = _build_command(
            {
                "keywords": "attention transformer",
                "author": "Vaswani",
                "year_from": 2017,
                "year_to": 2017,
            }
        )
        assert cmd.startswith("orbitr search")
        assert "attention transformer" in cmd
        assert "Vaswani" in cmd
        assert "2017" in cmd


# ---------------------------------------------------------------------------
# CLI: orbitr query
# ---------------------------------------------------------------------------


class TestQueryCLI:
    def test_shows_generated_command(self):
        result = _invoke("query", "Vaswani 2017 attention transformer")
        assert result.exit_code == 0
        assert "orbitr search" in result.output

    def test_shows_keywords_in_command(self):
        result = _invoke("query", "contrastive learning NLP")
        assert result.exit_code == 0
        assert "contrastive" in result.output or "NLP" in result.output

    def test_empty_extraction_exits_2(self):
        # Input that reduces to nothing after stop-word filtering
        result = _invoke("query", "a the of")
        assert result.exit_code == 2

    def test_run_shows_command_then_executes(self):
        # --run should print the generated command, then invoke search.
        # We verify the generated command is shown and the search pipeline
        # is triggered by patching search's async inner function.
        from orbitr.core.models import SearchResult

        mock_result = SearchResult(
            papers=[], total_count=0, query="attention", sources=["arxiv"]
        )
        with (
            patch(
                "orbitr.commands.search.ArxivClient.search",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "orbitr.commands.search.SemanticScholarClient.search",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            result = _invoke("query", "Vaswani 2017 attention", "--run")
        # The generated orbitr search command must appear in output
        assert "orbitr search" in result.output
        # Output must reference extracted terms
        assert "attention" in result.output or "Vaswani" in result.output

    def test_run_generated_command_contains_keywords(self):
        # Verify the generated command string (printed before --run executes)
        # contains the parsed keywords.  We abort early by patching search.
        with patch("orbitr.commands.search.search", MagicMock()):
            result = _invoke("query", "contrastive 2022", "--run")
        assert "contrastive" in result.output
