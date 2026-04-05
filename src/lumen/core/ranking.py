"""Ranking of deduplicated paper results.

Supported criteria:
  relevance  — TF-IDF query match against title + abstract
  citations  — log-scaled citation count (descending)
  date       — publication date recency (descending)
  impact     — citations × recency composite (descending)
  combined   — weighted composite of all signals
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Literal

from lumen.core.models import Paper

logger = logging.getLogger(__name__)

RankCriterion = Literal["relevance", "citations", "date", "impact", "combined"]

# Weights for the "combined" criterion (must sum to 1.0)
_COMBINED_WEIGHTS = {
    "relevance": 0.40,
    "citations": 0.35,
    "date": 0.25,
}

# Epoch reference for recency scoring (papers before this get 0)
_EPOCH = datetime(1990, 1, 1, tzinfo=timezone.utc)


def rank(
    papers: list[Paper],
    criterion: RankCriterion = "relevance",
    query: str | None = None,
) -> list[Paper]:
    """Sort papers by the chosen ranking criterion.

    Args:
        papers: Papers to rank.
        criterion: Ranking method to apply.
        query: Original search query (required for relevance-based scoring).

    Returns:
        Papers sorted from best to worst match.
    """
    if not papers:
        return []

    if criterion == "relevance":
        if not query:
            logger.warning(
                "No query provided for relevance ranking; falling back to date."
            )
            return rank(papers, "date")
        return sorted(papers, key=lambda p: _score_relevance(p, query), reverse=True)

    if criterion == "citations":
        return sorted(papers, key=_score_citations, reverse=True)

    if criterion == "date":
        return sorted(papers, key=_score_date, reverse=True)

    if criterion == "impact":
        return sorted(
            papers,
            key=lambda p: _score_citations(p) * _score_date(p),
            reverse=True,
        )

    if criterion == "combined":
        w = _COMBINED_WEIGHTS

        def _combined(p: Paper) -> float:
            rel = _score_relevance(p, query) if query else 0.0
            return (
                w["relevance"] * rel
                + w["citations"] * _score_citations(p)
                + w["date"] * _score_date(p)
            )

        return sorted(papers, key=_combined, reverse=True)

    raise ValueError(f"Unknown ranking criterion: {criterion!r}")


def _score_relevance(paper: Paper, query: str) -> float:
    """Score a paper by TF-IDF-like query match against title and abstract.

    Title matches are weighted 3×; abstract matches 1×. Each query term
    contributes independently so multi-word queries accumulate score.

    Args:
        paper: Paper to score.
        query: Search query string.

    Returns:
        Float relevance score (higher is better).
    """
    terms = query.lower().split()
    if not terms:
        return 0.0

    title_words = (paper.title or "").lower().split()
    abstract_words = (paper.abstract or "").lower().split()
    total_words = len(title_words) + len(abstract_words) or 1

    score = 0.0
    for term in terms:
        tf_title = title_words.count(term) * 3
        tf_abstract = abstract_words.count(term)
        score += (tf_title + tf_abstract) / total_words

    return score


def _score_citations(paper: Paper) -> float:
    """Return a log-scaled citation count score.

    Args:
        paper: Paper to score.

    Returns:
        Float score (0.0 if citation_count is None or zero).
    """
    count = paper.citation_count
    if not count:
        return 0.0
    return math.log1p(count)


def _score_date(paper: Paper) -> float:
    """Return a recency score based on publication date.

    Newer papers score higher. Papers with no date score 0.
    Score is normalised to [0, 1] against an epoch of 1990-01-01.

    Args:
        paper: Paper to score.

    Returns:
        Float recency score between 0.0 and 1.0.
    """
    dt = paper.published_date
    if dt is None:
        return 0.0

    now = datetime.now(tz=timezone.utc)
    total_span = (now - _EPOCH).total_seconds()
    paper_span = (dt - _EPOCH).total_seconds()

    if total_span <= 0:
        return 0.0
    return max(0.0, min(1.0, paper_span / total_span))
