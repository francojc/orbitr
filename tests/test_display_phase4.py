"""Tests for Phase 4 display layer: detail renderer, effective_format, pager flag.

Strategy
--------
- Test render_detail output via a Rich Console backed by a StringIO capture.
- Test effective_format() for TTY/non-TTY and explicit-override cases.
- Test that render() routes 'detail' to render_detail (not render_list fallback).
- Test that render() accepts pager=True without raising (pager inactive in test env).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from lumen.core.models import Author, Paper
from lumen.display import effective_format, render
from lumen.display.detail import render_detail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _paper(
    *,
    title: str = "Attention Is All You Need",
    authors: list[str] | None = None,
    abstract: str | None = "A groundbreaking paper on self-attention.",
    year: int = 2017,
    venue: str | None = "NeurIPS",
    doi: str | None = "10.1234/example",
    arxiv_id: str | None = "1706.03762",
    pdf_url: str | None = "https://arxiv.org/pdf/1706.03762",
    citation_count: int | None = 50000,
    source: str = "arxiv",
    categories: list[str] | None = None,
) -> Paper:
    author_objs = [
        Author(name=n, affiliation="MIT" if i == 0 else None)
        for i, n in enumerate(authors or ["Vaswani, Ashish", "Shazeer, Noam"])
    ]
    return Paper(
        id=f"{source}-1706",
        title=title,
        authors=author_objs,
        abstract=abstract,
        published_date=datetime(year, 6, 12, tzinfo=timezone.utc),
        url=f"https://arxiv.org/abs/{arxiv_id or 'test'}",
        pdf_url=pdf_url,
        doi=doi,
        arxiv_id=arxiv_id,
        venue=venue,
        categories=categories or ["cs.CL", "cs.LG"],
        citation_count=citation_count,
        source=source,
    )


def _capture(paper: Paper | None = None, papers: list[Paper] | None = None) -> str:
    """Render via render_detail into a string and return it."""
    buf = StringIO()
    con = Console(file=buf, no_color=True, width=100)
    if papers is not None:
        paper_list = papers
    elif paper is not None:
        paper_list = [paper]
    else:
        paper_list = [_paper()]
    render_detail(paper_list, console=con)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# render_detail — content tests
# ---------------------------------------------------------------------------


class TestRenderDetailContent:
    def test_title_present(self) -> None:
        out = _capture(_paper(title="Attention Is All You Need"))
        assert "Attention Is All You Need" in out

    def test_authors_present(self) -> None:
        out = _capture(_paper(authors=["Alice Smith", "Bob Jones"]))
        assert "Alice Smith" in out
        assert "Bob Jones" in out

    def test_affiliation_present(self) -> None:
        # First author has affiliation="MIT" from fixture
        out = _capture(_paper())
        assert "MIT" in out

    def test_abstract_present(self) -> None:
        out = _capture(_paper(abstract="A unique abstract string xyz123."))
        assert "A unique abstract string xyz123." in out

    def test_abstract_missing_placeholder(self) -> None:
        out = _capture(_paper(abstract=None))
        assert "No abstract available" in out

    def test_venue_in_meta(self) -> None:
        out = _capture(_paper(venue="NeurIPS 2017"))
        assert "NeurIPS 2017" in out

    def test_year_in_meta(self) -> None:
        out = _capture(_paper(year=2017))
        assert "2017" in out

    def test_doi_in_meta(self) -> None:
        out = _capture(_paper(doi="10.1234/example"))
        assert "10.1234/example" in out

    def test_arxiv_id_in_meta(self) -> None:
        out = _capture(_paper(arxiv_id="1706.03762"))
        assert "1706.03762" in out

    def test_citation_count_in_meta(self) -> None:
        out = _capture(_paper(citation_count=42000))
        assert "42000" in out

    def test_categories_in_meta(self) -> None:
        out = _capture(_paper(categories=["cs.CL", "cs.LG"]))
        assert "cs.CL" in out
        assert "cs.LG" in out

    def test_url_in_links(self) -> None:
        p = _paper(arxiv_id="1706.03762")
        out = _capture(p)
        assert p.url in out

    def test_pdf_url_in_links(self) -> None:
        out = _capture(_paper(pdf_url="https://arxiv.org/pdf/1706.03762"))
        assert "https://arxiv.org/pdf/1706.03762" in out

    def test_no_pdf_url_omitted(self) -> None:
        out = _capture(_paper(pdf_url=None))
        assert "PDF" not in out

    def test_semantic_scholar_source_badge(self) -> None:
        out = _capture(_paper(source="semantic_scholar"))
        assert "Semantic Scholar" in out

    def test_arxiv_source_badge(self) -> None:
        out = _capture(_paper(source="arxiv"))
        assert "arXiv" in out

    def test_no_papers_prints_placeholder(self) -> None:
        out = _capture(papers=[])
        assert "No results" in out

    def test_multiple_papers_separated(self) -> None:
        p1 = _paper(title="First Paper")
        p2 = _paper(title="Second Paper")
        out = _capture(papers=[p1, p2])
        assert "First Paper" in out
        assert "Second Paper" in out

    def test_no_authors_placeholder(self) -> None:
        p = _paper()
        p = p.model_copy(update={"authors": []})
        out = _capture(p)
        assert "Unknown authors" in out

    def test_no_meta_rows_when_sparse(self) -> None:
        """Paper with minimal fields should still render without error."""
        p = Paper(
            id="min-1",
            title="Minimal Paper",
            authors=[],
            url="https://example.com",
            source="arxiv",
        )
        out = _capture(p)
        assert "Minimal Paper" in out


# ---------------------------------------------------------------------------
# effective_format — TTY detection
# ---------------------------------------------------------------------------


class TestEffectiveFormat:
    def test_explicit_overrides_all(self) -> None:
        with patch.object(sys.stdout, "isatty", return_value=False):
            assert effective_format("list", "table") == "list"

    def test_explicit_overrides_tty(self) -> None:
        with patch.object(sys.stdout, "isatty", return_value=True):
            assert effective_format("detail", "table") == "detail"

    def test_non_tty_defaults_to_json(self) -> None:
        with patch.object(sys.stdout, "isatty", return_value=False):
            assert effective_format(None, "table") == "json"

    def test_tty_uses_config_default(self) -> None:
        with patch.object(sys.stdout, "isatty", return_value=True):
            assert effective_format(None, "table") == "table"

    def test_tty_uses_config_default_list(self) -> None:
        with patch.object(sys.stdout, "isatty", return_value=True):
            assert effective_format(None, "list") == "list"

    def test_non_tty_ignores_config_default(self) -> None:
        with patch.object(sys.stdout, "isatty", return_value=False):
            assert effective_format(None, "list") == "json"


# ---------------------------------------------------------------------------
# render() — routing and pager flag
# ---------------------------------------------------------------------------


class TestRenderDispatch:
    def _render(self, papers: list[Paper], fmt: str, **kwargs) -> str:
        buf = StringIO()
        con = Console(file=buf, no_color=True, width=100)
        render(papers, fmt=fmt, console=con, **kwargs)  # type: ignore[arg-type]
        return buf.getvalue()

    def test_detail_format_uses_render_detail(self) -> None:
        """render() with fmt='detail' should show full paper content, not truncated list."""
        p = _paper(abstract="Unique detail marker ABCXYZ987.")
        out = self._render([p], "detail")
        # Full abstract should appear (detail), not snippet (list)
        assert "Unique detail marker ABCXYZ987." in out

    def test_table_format_routes_correctly(self) -> None:
        p = _paper(title="Table Route Test")
        out = self._render([p], "table")
        assert "Table Route Test" in out

    def test_list_format_routes_correctly(self) -> None:
        p = _paper(title="List Route Test")
        out = self._render([p], "list")
        assert "List Route Test" in out

    def test_pager_false_renders_normally(self) -> None:
        p = _paper(title="Pager Off Test")
        out = self._render([p], "table", pager=False)
        assert "Pager Off Test" in out

    def test_pager_true_non_tty_renders_normally(self) -> None:
        """pager=True but stdout not a TTY — should render without paging."""
        p = _paper(title="Pager NonTTY Test")
        with patch.object(sys.stdout, "isatty", return_value=False):
            out = self._render([p], "table", pager=True)
        assert "Pager NonTTY Test" in out

    def test_json_format_bypasses_pager(self) -> None:
        """JSON format should never go through the pager."""
        p = _paper(title="JSON Pager Test")
        buf = StringIO()
        with patch.object(sys.stdout, "isatty", return_value=True):
            render([p], fmt="json", file=buf, pager=True)  # type: ignore[arg-type]
        assert "JSON Pager Test" in buf.getvalue()

    def test_unknown_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown format"):
            render([_paper()], fmt="invalid")  # type: ignore[arg-type]
