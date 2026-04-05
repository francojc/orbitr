"""Unit tests for lumen.core.deduplication."""

from __future__ import annotations

from lumen.core.deduplication import (
    _authors_overlap,
    _merge,
    _title_similarity,
    deduplicate,
)
from lumen.core.models import Author, Paper

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _paper(
    *,
    title: str = "Default Title",
    doi: str | None = None,
    arxiv_id: str | None = None,
    source: str = "arxiv",
    authors: list[str] | None = None,
    citation_count: int | None = None,
    abstract: str | None = None,
    categories: list[str] | None = None,
) -> Paper:
    return Paper(
        id=f"{source}:{title[:10]}",
        title=title,
        url=f"https://example.com/{title[:10]}",
        source=source,
        doi=doi,
        arxiv_id=arxiv_id,
        authors=[Author(name=n) for n in (authors or [])],
        citation_count=citation_count,
        abstract=abstract,
        categories=categories or [],
    )


# ---------------------------------------------------------------------------
# _title_similarity
# ---------------------------------------------------------------------------


class TestTitleSimilarity:
    def test_identical_titles(self):
        assert (
            _title_similarity("Attention Is All You Need", "Attention Is All You Need")
            == 1.0
        )

    def test_case_insensitive(self):
        score = _title_similarity(
            "attention is all you need", "ATTENTION IS ALL YOU NEED"
        )
        assert score == 1.0

    def test_different_titles(self):
        score = _title_similarity(
            "Deep Learning for NLP", "Computer Vision Transformers"
        )
        assert score < 0.5

    def test_empty_strings(self):
        # Two empty strings are 100% similar (identical); rapidfuzz agrees.
        # Dedup guards against false positives via author-overlap check.
        assert _title_similarity("", "") == 1.0

    def test_partial_overlap(self):
        score = _title_similarity(
            "Attention Is All You Need",
            "Attention Is All You Need: A Survey",
        )
        assert score > 0.80


# ---------------------------------------------------------------------------
# _authors_overlap
# ---------------------------------------------------------------------------


class TestAuthorsOverlap:
    def test_shared_surname(self):
        a = _paper(authors=["Alice Smith", "Bob Jones"])
        b = _paper(authors=["Carol Smith", "Dave Lee"])
        assert _authors_overlap(a, b) is True

    def test_no_overlap(self):
        a = _paper(authors=["Alice Smith"])
        b = _paper(authors=["Bob Jones"])
        assert _authors_overlap(a, b) is False

    def test_empty_author_list_a(self):
        a = _paper(authors=[])
        b = _paper(authors=["Bob Jones"])
        assert _authors_overlap(a, b) is True  # fall back to True

    def test_empty_author_list_both(self):
        a = _paper(authors=[])
        b = _paper(authors=[])
        assert _authors_overlap(a, b) is True


# ---------------------------------------------------------------------------
# _merge
# ---------------------------------------------------------------------------


class TestMerge:
    def test_fills_missing_abstract(self):
        winner = _paper(title="Test", abstract=None)
        dup = _paper(title="Test", abstract="Very useful abstract.")
        merged = _merge(winner, dup)
        assert merged.abstract == "Very useful abstract."

    def test_fills_missing_doi(self):
        winner = _paper(title="Test", doi=None)
        dup = _paper(title="Test", doi="10.1234/xyz")
        merged = _merge(winner, dup)
        assert merged.doi == "10.1234/xyz"

    def test_takes_max_citation_count(self):
        winner = _paper(title="Test", citation_count=100)
        dup = _paper(title="Test", citation_count=5000)
        merged = _merge(winner, dup)
        assert merged.citation_count == 5000

    def test_winner_citations_preserved_when_higher(self):
        winner = _paper(title="Test", citation_count=9000)
        dup = _paper(title="Test", citation_count=50)
        merged = _merge(winner, dup)
        assert merged.citation_count == 9000

    def test_prefers_richer_author_list(self):
        poor = _paper(title="Test", authors=["Alice"])
        rich = _paper(title="Test", authors=["Alice", "Bob", "Carol"])
        merged = _merge(poor, rich)
        assert len(merged.authors) == 3

    def test_merges_categories_without_duplicates(self):
        winner = _paper(title="Test", categories=["cs.LG"])
        dup = _paper(title="Test", categories=["cs.LG", "cs.CL"])
        merged = _merge(winner, dup)
        assert set(merged.categories) == {"cs.LG", "cs.CL"}
        assert merged.categories.count("cs.LG") == 1


# ---------------------------------------------------------------------------
# deduplicate
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_no_duplicates_unchanged(self):
        papers = [
            _paper(title="Paper One", doi="10.1/a"),
            _paper(title="Paper Two", doi="10.1/b"),
            _paper(title="Paper Three", doi="10.1/c"),
        ]
        result = deduplicate(papers)
        assert len(result) == 3

    def test_exact_doi_dedup(self):
        a = _paper(
            title="Attention Is All You Need", doi="10.1234/attn", source="arxiv"
        )
        b = _paper(
            title="Attention Is All You Need",
            doi="10.1234/attn",
            source="semantic_scholar",
            citation_count=50000,
        )
        result = deduplicate([a, b])
        assert len(result) == 1
        assert result[0].citation_count == 50000

    def test_exact_arxiv_id_dedup(self):
        a = _paper(title="Transformers", arxiv_id="1706.03762", source="arxiv")
        b = _paper(
            title="Transformers (SS)",
            arxiv_id="1706.03762",
            source="semantic_scholar",
            citation_count=200,
        )
        result = deduplicate([a, b])
        assert len(result) == 1
        assert result[0].citation_count == 200

    def test_fuzzy_title_dedup(self):
        a = _paper(title="Attention Is All You Need", authors=["Vaswani"])
        b = _paper(
            title="Attention is All You Need",
            authors=["Vaswani"],
            source="semantic_scholar",
        )
        result = deduplicate([a, b])
        assert len(result) == 1

    def test_fuzzy_title_no_author_overlap_not_deduped(self):
        a = _paper(title="Attention Is All You Need", authors=["Vaswani"])
        b = _paper(
            title="Attention Is All You Need",
            authors=["LeCun"],
            source="semantic_scholar",
        )
        result = deduplicate([a, b])
        assert len(result) == 2

    def test_empty_list(self):
        assert deduplicate([]) == []

    def test_single_paper_unchanged(self):
        papers = [_paper(title="Solo Paper")]
        result = deduplicate(papers)
        assert len(result) == 1

    def test_three_sources_merged_to_one(self):
        a = _paper(
            title="Attention Is All You Need",
            arxiv_id="1706.03762",
            source="arxiv",
            citation_count=100,
        )
        b = _paper(
            title="Attention Is All You Need",
            arxiv_id="1706.03762",
            source="semantic_scholar",
            citation_count=170000,
        )
        c = _paper(
            title="Attention Is All You Need",
            arxiv_id="1706.03762",
            source="other",
            abstract="The abstract.",
        )
        result = deduplicate([a, b, c])
        assert len(result) == 1
        assert result[0].citation_count == 170000
        assert result[0].abstract == "The abstract."

    def test_preserves_order_of_unique_papers(self):
        papers = [
            _paper(title="Alpha Paper"),
            _paper(title="Beta Paper"),
            _paper(title="Gamma Paper"),
        ]
        result = deduplicate(papers)
        assert [p.title for p in result] == ["Alpha Paper", "Beta Paper", "Gamma Paper"]
