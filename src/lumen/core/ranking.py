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
    # TODO: implement in Phase 2
    raise NotImplementedError


def _score_relevance(paper: Paper, query: str) -> float:
    """Score a paper by TF-IDF-like query match against title and abstract.

    Args:
        paper: Paper to score.
        query: Search query string.

    Returns:
        Float relevance score (higher is better).
    """
    # TODO: implement in Phase 2
    raise NotImplementedError


def _score_citations(paper: Paper) -> float:
    """Return a log-scaled citation count score.

    Args:
        paper: Paper to score.

    Returns:
        Float score (0.0 if citation_count is None).
    """
    # TODO: implement in Phase 2
    raise NotImplementedError


def _score_date(paper: Paper) -> float:
    """Return a recency score based on publication date.

    Newer papers score higher. Papers with no date score 0.

    Args:
        paper: Paper to score.

    Returns:
        Float recency score between 0.0 and 1.0.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError
