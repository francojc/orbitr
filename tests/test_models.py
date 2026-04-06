"""Unit tests for orbitr.core.models: Paper, Author, SearchResult."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from orbitr.core.models import Author, Paper, SearchResult

# ---------------------------------------------------------------------------
# Author
# ---------------------------------------------------------------------------


class TestAuthor:
    def test_minimal(self):
        a = Author(name="Jane Doe")
        assert a.name == "Jane Doe"
        assert a.affiliation is None
        assert a.author_id is None

    def test_full(self):
        a = Author(name="Jane Doe", affiliation="MIT", author_id="auth-123")
        assert a.affiliation == "MIT"
        assert a.author_id == "auth-123"

    def test_name_required(self):
        with pytest.raises(ValidationError):
            Author()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------


def _paper(**overrides) -> Paper:
    """Return a minimal valid Paper, optionally overriding fields."""
    defaults = dict(
        id="arxiv:1706.03762",
        title="Attention Is All You Need",
        url="https://arxiv.org/abs/1706.03762",
        source="arxiv",
    )
    defaults.update(overrides)
    return Paper(**defaults)


class TestPaper:
    def test_minimal(self):
        p = _paper()
        assert p.id == "arxiv:1706.03762"
        assert p.title == "Attention Is All You Need"
        assert p.source == "arxiv"
        assert p.authors == []
        assert p.categories == []
        assert p.abstract is None
        assert p.doi is None
        assert p.arxiv_id is None
        assert p.citation_count is None

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Paper(title="No ID or URL", source="arxiv")  # type: ignore[call-arg]

    def test_with_authors(self):
        authors = [Author(name="Alice"), Author(name="Bob")]
        p = _paper(authors=authors)
        assert p.author_names == ["Alice", "Bob"]

    def test_author_names_empty(self):
        p = _paper()
        assert p.author_names == []

    def test_year_from_published_date(self):
        dt = datetime(2017, 6, 12, tzinfo=timezone.utc)
        p = _paper(published_date=dt)
        assert p.year == 2017

    def test_year_none_when_no_date(self):
        p = _paper()
        assert p.year is None

    def test_optional_fields(self):
        dt = datetime(2017, 6, 12, tzinfo=timezone.utc)
        p = _paper(
            abstract="Transformers are cool.",
            published_date=dt,
            updated_date=dt,
            pdf_url="https://arxiv.org/pdf/1706.03762",
            doi="10.1234/example",
            arxiv_id="1706.03762",
            venue="NeurIPS",
            categories=["cs.LG", "cs.CL"],
            citation_count=50000,
        )
        assert p.abstract == "Transformers are cool."
        assert p.pdf_url == "https://arxiv.org/pdf/1706.03762"
        assert p.doi == "10.1234/example"
        assert p.arxiv_id == "1706.03762"
        assert p.venue == "NeurIPS"
        assert p.categories == ["cs.LG", "cs.CL"]
        assert p.citation_count == 50000

    def test_json_round_trip(self):
        dt = datetime(2017, 6, 12, tzinfo=timezone.utc)
        p = _paper(published_date=dt, authors=[Author(name="Alice")])
        restored = Paper.model_validate_json(p.model_dump_json())
        assert restored == p


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResult:
    def test_minimal(self):
        sr = SearchResult(query="transformers")
        assert sr.query == "transformers"
        assert sr.papers == []
        assert sr.total_count == 0
        assert sr.sources == []

    def test_query_required(self):
        with pytest.raises(ValidationError):
            SearchResult()  # type: ignore[call-arg]

    def test_with_papers(self):
        papers = [
            _paper(
                id=f"arxiv:{i}",
                title=f"Paper {i}",
                url=f"https://arxiv.org/abs/{i}",
                source="arxiv",
            )
            for i in range(3)
        ]
        sr = SearchResult(query="test", papers=papers, total_count=3, sources=["arxiv"])
        assert len(sr.papers) == 3
        assert sr.total_count == 3
        assert sr.sources == ["arxiv"]

    def test_json_round_trip(self):
        papers = [_paper()]
        sr = SearchResult(
            query="attention", papers=papers, total_count=1, sources=["arxiv"]
        )
        restored = SearchResult.model_validate_json(sr.model_dump_json())
        assert restored == sr
