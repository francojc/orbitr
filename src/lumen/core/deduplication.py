"""Deduplication of results from multiple sources.

Strategy (applied in order):
1. Exact DOI match
2. Exact arXiv ID match
3. Fuzzy title + author overlap (≥ 85 % similarity via rapidfuzz)

When a duplicate is detected, metadata is merged: the paper with the
richer record (more authors, non-null abstract, higher citation count)
is kept; fields missing from the winner are filled from the duplicate.
"""

from __future__ import annotations

import logging

from lumen.core.models import Paper

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.85


def deduplicate(
    papers: list[Paper], threshold: float = _DEFAULT_THRESHOLD
) -> list[Paper]:
    """Remove duplicate papers from a combined multi-source result list.

    Args:
        papers: Combined list of papers from all sources.
        threshold: Fuzzy title similarity threshold (0–1). Papers above
            this threshold with overlapping authors are considered duplicates.

    Returns:
        Deduplicated list preserving the richer record.
    """
    seen: list[Paper] = []

    for paper in papers:
        match_idx = _find_duplicate(paper, seen, threshold)
        if match_idx is None:
            seen.append(paper)
        else:
            seen[match_idx] = _merge(seen[match_idx], paper)
            logger.debug(
                "Merged duplicate: '%s' (%s) into '%s' (%s)",
                paper.title[:40],
                paper.source,
                seen[match_idx].title[:40],
                seen[match_idx].source,
            )

    return seen


def _find_duplicate(
    candidate: Paper, pool: list[Paper], threshold: float
) -> int | None:
    """Return the index of a matching paper in pool, or None.

    Matching proceeds in priority order: exact DOI, exact arXiv ID, fuzzy title.

    Args:
        candidate: The incoming paper to check.
        pool: Papers already accepted into the deduplicated set.
        threshold: Fuzzy title similarity threshold.

    Returns:
        Index into pool, or None if no match found.
    """
    for idx, existing in enumerate(pool):
        # 1. Exact DOI
        if candidate.doi and existing.doi and candidate.doi == existing.doi:
            return idx
        # 2. Exact arXiv ID
        if (
            candidate.arxiv_id
            and existing.arxiv_id
            and candidate.arxiv_id == existing.arxiv_id
        ):
            return idx
        # 3. Fuzzy title + author overlap
        if _title_similarity(
            candidate.title, existing.title
        ) >= threshold and _authors_overlap(candidate, existing):
            return idx
    return None


def _authors_overlap(a: Paper, b: Paper) -> bool:
    """Return True if the two papers share at least one author surname.

    Falls back to True (assume match) when either paper has no authors,
    to avoid discarding real duplicates with incomplete metadata.

    Args:
        a: First paper.
        b: Second paper.

    Returns:
        True if at least one surname overlaps or either author list is empty.
    """
    if not a.authors or not b.authors:
        return True
    surnames_a = {name.split()[-1].lower() for name in a.author_names}
    surnames_b = {name.split()[-1].lower() for name in b.author_names}
    return bool(surnames_a & surnames_b)


def _merge(winner: Paper, duplicate: Paper) -> Paper:
    """Merge metadata from a duplicate into the winner record.

    The winner is the record with richer metadata (more authors, non-null
    abstract, higher citation count). Fields that are None in the winner
    are filled from the duplicate. Citation counts take the maximum.

    Args:
        winner: The record to keep.
        duplicate: The record to merge from.

    Returns:
        Merged Paper instance (winner identity preserved).
    """
    # Prefer the record with more authors
    if len(duplicate.authors) > len(winner.authors):
        winner, duplicate = duplicate, winner

    fields: dict = winner.model_dump()

    # Fill None fields from duplicate
    for field in (
        "abstract",
        "doi",
        "arxiv_id",
        "venue",
        "pdf_url",
        "published_date",
        "updated_date",
    ):
        if fields[field] is None:
            dup_val = getattr(duplicate, field)
            if dup_val is not None:
                fields[field] = dup_val

    # Take the higher citation count
    if duplicate.citation_count is not None:
        if fields["citation_count"] is None:
            fields["citation_count"] = duplicate.citation_count
        else:
            fields["citation_count"] = max(
                fields["citation_count"], duplicate.citation_count
            )

    # Merge categories without duplicates, preserving order
    extra_cats = [c for c in duplicate.categories if c not in fields["categories"]]
    fields["categories"] = fields["categories"] + extra_cats

    return Paper(**fields)


def _title_similarity(a: str, b: str) -> float:
    """Compute normalised title similarity using rapidfuzz.

    Args:
        a: First title string.
        b: Second title string.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    try:
        from rapidfuzz import fuzz

        return fuzz.token_sort_ratio(a.lower(), b.lower()) / 100.0
    except ImportError:
        # Fall back to a simple character overlap if rapidfuzz is unavailable.
        logger.warning(
            "rapidfuzz not available; falling back to basic title comparison."
        )
        a_set = set(a.lower().split())
        b_set = set(b.lower().split())
        if not a_set or not b_set:
            return 0.0
        return len(a_set & b_set) / len(a_set | b_set)
