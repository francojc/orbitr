"""Tests for core/export.py formatters and the orbitr export command."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from orbitr.cli import app
from orbitr.config import Config, Credentials
from orbitr.core.export import to_bibtex, to_csl_json, to_ris
from orbitr.core.models import Author, Paper

runner = CliRunner()

_CREDS = Credentials()


def _test_config(**overrides) -> Config:
    base = Config(
        format="table",
        no_cache=True,
        max_results=5,
        credentials=_CREDS,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _paper(
    title: str = "Attention Is All You Need",
    year: int = 2017,
    doi: str | None = "10.48550/arXiv.1706.03762",
    venue: str | None = "arXiv",
    abstract: str | None = "Transformer paper.",
) -> Paper:
    return Paper(
        id="ss:vaswani2017",
        title=title,
        authors=[
            Author(name="Ashish Vaswani"),
            Author(name="Noam Shazeer"),
        ],
        abstract=abstract,
        published_date=datetime(year, 6, 12, tzinfo=timezone.utc),
        url="https://arxiv.org/abs/1706.03762",
        source="semantic_scholar",
        doi=doi,
        venue=venue,
        citation_count=100_000,
    )


def _invoke(*args: str, config: Config | None = None, input: str | None = None):
    cfg = config or _test_config()
    with patch("orbitr.config.load_config", return_value=cfg):
        return runner.invoke(app, list(args), input=input)


# ---------------------------------------------------------------------------
# Unit tests: to_bibtex
# ---------------------------------------------------------------------------


class TestToBibtex:
    def test_entry_type(self):
        out = to_bibtex([_paper()])
        assert "@article{" in out

    def test_citation_key(self):
        out = to_bibtex([_paper()])
        assert "Vaswani2017" in out

    def test_title_field(self):
        out = to_bibtex([_paper(title="My Test Title")])
        assert "My Test Title" in out

    def test_authors_joined_with_and(self):
        out = to_bibtex([_paper()])
        assert "Ashish Vaswani and Noam Shazeer" in out

    def test_year_field(self):
        out = to_bibtex([_paper(year=2017)])
        assert "year      = {2017}" in out

    def test_doi_field(self):
        out = to_bibtex([_paper(doi="10.1234/test")])
        assert "10.1234/test" in out

    def test_venue_as_journal(self):
        out = to_bibtex([_paper(venue="NeurIPS")])
        assert "NeurIPS" in out

    def test_multiple_papers(self):
        papers = [_paper(f"Paper {i}") for i in range(3)]
        out = to_bibtex(papers)
        assert out.count("@article{") == 3

    def test_empty_list(self):
        assert to_bibtex([]) == ""

    def test_unknown_year_in_key(self):
        p = _paper()
        object.__setattr__(p, "published_date", None)
        out = to_bibtex([p])
        assert "XXXX" in out


# ---------------------------------------------------------------------------
# Unit tests: to_ris
# ---------------------------------------------------------------------------


class TestToRis:
    def test_starts_with_ty(self):
        out = to_ris([_paper()])
        assert out.startswith("TY  - JOUR")

    def test_ends_with_er(self):
        out = to_ris([_paper()])
        assert "ER  -" in out

    def test_title_field(self):
        out = to_ris([_paper(title="RIS Test")])
        assert "TI  - RIS Test" in out

    def test_author_fields(self):
        out = to_ris([_paper()])
        assert "AU  - Ashish Vaswani" in out
        assert "AU  - Noam Shazeer" in out

    def test_year_field(self):
        out = to_ris([_paper(year=2017)])
        assert "PY  - 2017" in out

    def test_doi_field(self):
        out = to_ris([_paper(doi="10.1234/xyz")])
        assert "DO  - 10.1234/xyz" in out

    def test_multiple_records(self):
        papers = [_paper(f"Paper {i}") for i in range(3)]
        out = to_ris(papers)
        assert out.count("TY  - JOUR") == 3
        assert out.count("ER  -") == 3

    def test_empty_list(self):
        assert to_ris([]) == ""


# ---------------------------------------------------------------------------
# Unit tests: to_csl_json
# ---------------------------------------------------------------------------


class TestToCslJson:
    def test_returns_json_array(self):
        out = to_csl_json([_paper()])
        items = json.loads(out)
        assert isinstance(items, list)
        assert len(items) == 1

    def test_item_has_required_fields(self):
        out = to_csl_json([_paper()])
        item = json.loads(out)[0]
        assert "id" in item
        assert item["type"] == "article-journal"
        assert item["title"] == "Attention Is All You Need"

    def test_author_structure(self):
        out = to_csl_json([_paper()])
        item = json.loads(out)[0]
        assert item["author"][0]["family"] == "Vaswani"
        assert item["author"][0]["given"] == "Ashish"

    def test_issued_year(self):
        out = to_csl_json([_paper(year=2017)])
        item = json.loads(out)[0]
        assert item["issued"]["date-parts"] == [[2017]]

    def test_doi_present(self):
        out = to_csl_json([_paper(doi="10.1234/test")])
        item = json.loads(out)[0]
        assert item["DOI"] == "10.1234/test"

    def test_multiple_papers(self):
        papers = [_paper(f"Paper {i}") for i in range(4)]
        out = to_csl_json(papers)
        assert len(json.loads(out)) == 4

    def test_empty_list(self):
        items = json.loads(to_csl_json([]))
        assert items == []


# ---------------------------------------------------------------------------
# CLI: orbitr export (stdin path)
# ---------------------------------------------------------------------------


class TestExportStdin:
    def _ndjson(self, papers: list[Paper]) -> str:
        return "\n".join(p.model_dump_json() for p in papers) + "\n"

    def test_bibtex_from_stdin(self):
        ndjson = self._ndjson([_paper()])
        result = _invoke("export", "--format", "bibtex", input=ndjson)
        assert result.exit_code == 0
        assert "@article{" in result.output

    def test_ris_from_stdin(self):
        ndjson = self._ndjson([_paper()])
        result = _invoke("export", "--format", "ris", input=ndjson)
        assert result.exit_code == 0
        assert "TY  - JOUR" in result.output

    def test_csl_json_from_stdin(self):
        ndjson = self._ndjson([_paper()])
        result = _invoke("export", "--format", "csl-json", input=ndjson)
        assert result.exit_code == 0
        items = json.loads(result.output)
        assert len(items) == 1

    def test_output_to_file(self):
        ndjson = self._ndjson([_paper()])
        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = Path(tmpdir) / "refs.bib"
            result = _invoke(
                "export", "--format", "bibtex", "--output", str(outfile), input=ndjson
            )
        assert result.exit_code == 0
        assert "Exported" in result.output

    def test_invalid_format_exits_2(self):
        result = _invoke("export", "--format", "endnote", input="")
        assert result.exit_code == 2

    def test_empty_stdin_exits_4(self):
        result = _invoke("export", "--format", "bibtex", input="\n\n")
        assert result.exit_code == 4

    def test_multiple_papers_from_stdin(self):
        papers = [_paper(f"Paper {i}") for i in range(3)]
        ndjson = self._ndjson(papers)
        result = _invoke("export", "--format", "bibtex", input=ndjson)
        assert result.exit_code == 0
        assert result.output.count("@article{") == 3


# ---------------------------------------------------------------------------
# CLI: orbitr export --query
# ---------------------------------------------------------------------------


class TestExportQuery:
    def test_query_exports_results(self):
        papers = [_paper()]
        with (
            patch(
                "orbitr.clients.arxiv.ArxivClient.search", new_callable=AsyncMock
            ) as ax,
            patch(
                "orbitr.clients.semantic_scholar.SemanticScholarClient.search",
                new_callable=AsyncMock,
            ) as ss,
        ):
            from orbitr.core.models import SearchResult

            ax.return_value = SearchResult(
                papers=papers, total_count=1, query="test", sources=["arxiv"]
            )
            ss.return_value = SearchResult(
                papers=[], total_count=0, query="test", sources=["semantic_scholar"]
            )
            result = _invoke("export", "--query", "transformers", "--format", "bibtex")
        assert result.exit_code == 0
        assert "@article{" in result.output
