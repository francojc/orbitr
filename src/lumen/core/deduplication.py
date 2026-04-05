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
    # TODO: implement in Phase 2
    raise NotImplementedError


def _merge(winner: Paper, duplicate: Paper) -> Paper:
    """Merge metadata from a duplicate into the winner record.

    Fields that are None in the winner are filled from the duplicate.
    Citation counts take the maximum of both records.

    Args:
        winner: The record to keep (richer metadata).
        duplicate: The record to merge from.

    Returns:
        Merged Paper instance.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError


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
