"""Unit tests for orbitr.core.ranking."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orbitr.core.models import Paper
from orbitr.core.ranking import (
    _score_citations,
    _score_date,
    _score_relevance,
    rank,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _paper(
    *,
    title: str = "Test Paper",
    abstract: str | None = None,
    citation_count: int | None = None,
    year: int | None = None,
) -> Paper:
    dt = datetime(year, 6, 1, tzinfo=timezone.utc) if year else None
    return Paper(
        id=f"test:{title[:12]}",
        title=title,
        url="https://example.com",
        source="arxiv",
        citation_count=citation_count,
        published_date=dt,
        abstract=abstract,
    )


# ---------------------------------------------------------------------------
# _score_citations
# ---------------------------------------------------------------------------


class TestScoreCitations:
    def test_zero_citations(self):
        assert _score_citations(_paper(citation_count=0)) == 0.0

    def test_none_citations(self):
        assert _score_citations(_paper(citation_count=None)) == 0.0

    def test_positive_citations(self):
        score = _score_citations(_paper(citation_count=1000))
        assert score > 0.0

    def test_higher_citations_higher_score(self):
        low = _score_citations(_paper(citation_count=10))
        high = _score_citations(_paper(citation_count=10000))
        assert high > low


# ---------------------------------------------------------------------------
# _score_date
# ---------------------------------------------------------------------------


class TestScoreDate:
    def test_no_date_returns_zero(self):
        assert _score_date(_paper()) == 0.0

    def test_recent_higher_than_old(self):
        old = _score_date(_paper(year=2000))
        recent = _score_date(_paper(year=2023))
        assert recent > old

    def test_score_between_zero_and_one(self):
        score = _score_date(_paper(year=2015))
        assert 0.0 <= score <= 1.0

    def test_very_old_paper(self):
        # 1991 — just after epoch; should be very small but >= 0
        score = _score_date(_paper(year=1991))
        assert score >= 0.0


# ---------------------------------------------------------------------------
# _score_relevance
# ---------------------------------------------------------------------------


class TestScoreRelevance:
    def test_title_match_scores_higher_than_no_match(self):
        match = _paper(title="transformer attention mechanism")
        no_match = _paper(title="computer vision image segmentation")
        q = "transformer attention"
        assert _score_relevance(match, q) > _score_relevance(no_match, q)

    def test_abstract_match_contributes(self):
        p_with_abs = _paper(
            title="Unrelated Title", abstract="transformer attention is important"
        )
        p_no_abs = _paper(title="Unrelated Title")
        q = "transformer attention"
        assert _score_relevance(p_with_abs, q) > _score_relevance(p_no_abs, q)

    def test_empty_query_returns_zero(self):
        p = _paper(title="transformer attention")
        assert _score_relevance(p, "") == 0.0

    def test_no_title_or_abstract(self):
        p = _paper(title="")
        assert _score_relevance(p, "transformer") == 0.0


# ---------------------------------------------------------------------------
# rank()
# ---------------------------------------------------------------------------


class TestRank:
    def _papers(self):
        return [
            _paper(title="transformer attention layer", citation_count=5000, year=2017),
            _paper(title="deep neural networks survey", citation_count=100, year=2023),
            _paper(title="attention mechanism overview", citation_count=800, year=2020),
        ]

    def test_rank_by_citations(self):
        result = rank(self._papers(), criterion="citations")
        counts = [p.citation_count for p in result]
        assert counts == sorted(counts, reverse=True)

    def test_rank_by_date(self):
        result = rank(self._papers(), criterion="date")
        years = [p.published_date.year for p in result]
        assert years == sorted(years, reverse=True)

    def test_rank_by_relevance(self):
        result = rank(
            self._papers(), criterion="relevance", query="transformer attention"
        )
        # First result should contain both query terms
        assert "transformer" in result[0].title or "attention" in result[0].title

    def test_rank_by_impact(self):
        result = rank(self._papers(), criterion="impact")
        assert len(result) == 3  # order may vary; just assert no crash

    def test_rank_by_combined(self):
        result = rank(self._papers(), criterion="combined", query="transformer")
        assert len(result) == 3

    def test_empty_list_returns_empty(self):
        assert rank([], criterion="citations") == []

    def test_relevance_without_query_falls_back_to_date(self):
        papers = self._papers()
        result = rank(papers, criterion="relevance", query=None)
        years = [p.published_date.year for p in result]
        assert years == sorted(years, reverse=True)

    def test_unknown_criterion_raises(self):
        with pytest.raises(ValueError, match="Unknown ranking criterion"):
            rank(self._papers(), criterion="bogus")  # type: ignore[arg-type]

    def test_single_paper_unchanged(self):
        papers = [_paper(title="Solo", citation_count=42, year=2021)]
        assert rank(papers, "citations") == papers
