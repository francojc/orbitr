"""Query string helpers: field-filter parsing and per-source translation.

lumen accepts a simple ``field:value`` syntax in the query string:

    lumen search "title:transformers author:Vaswani"
    lumen search "BERT" --title "contrastive learning" --author "Gao"

These helpers translate user-facing filters into the query dialect each
source API expects, and produce stable cache-key strings.
"""

from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# Field-filter parsing
# ---------------------------------------------------------------------------

_FIELD_RE = re.compile(
    r'\b(title|author|venue|abstract):"([^"]+)"'  # quoted: title:"deep learning"
    r"|\b(title|author|venue|abstract):(\S+)",  # unquoted: title:transformers
    re.IGNORECASE,
)


def parse_query(raw: str) -> tuple[str, dict[str, str]]:
    """Split a raw query into a keyword base and extracted field filters.

    Supported field names: ``title``, ``author``, ``venue``, ``abstract``.

    Args:
        raw: User-supplied query string, e.g. ``"BERT title:contextual embeddings"``.

    Returns:
        A ``(base_keywords, filters)`` tuple where *base_keywords* is the
        query with all ``field:value`` tokens removed and *filters* is a
        ``{field: value}`` dict for any fields found.

    Examples::

        >>> parse_query('BERT title:"contextual embeddings" author:Devlin')
        ('BERT', {'title': 'contextual embeddings', 'author': 'Devlin'})
    """
    filters: dict[str, str] = {}
    remainder = raw

    for m in _FIELD_RE.finditer(raw):
        field = (m.group(1) or m.group(3)).lower()
        value = m.group(2) or m.group(4)
        # Last occurrence wins (consistent with CLI --option semantics).
        filters[field] = value
        remainder = remainder.replace(m.group(0), "", 1)

    base = " ".join(remainder.split())  # normalise whitespace
    return base, filters


# ---------------------------------------------------------------------------
# arXiv query builder
# ---------------------------------------------------------------------------

# Mapping from lumen field names to arXiv field prefix codes.
_ARXIV_FIELD: dict[str, str] = {
    "title": "ti",
    "author": "au",
    "abstract": "abs",
    "venue": "jr",  # journal-ref — best-effort
}


def build_arxiv_query(
    base: str,
    filters: dict[str, str],
    *,
    extra_title: str | None = None,
    extra_author: str | None = None,
) -> str:
    """Build an arXiv-style boolean query from base keywords and filters.

    arXiv supports field prefixes via ``ti:``, ``au:``, ``abs:``, ``jr:``.
    Multiple clauses are joined with ``AND``.

    Args:
        base: Free-text keywords (no field prefix).
        filters: Field-value dict from :func:`parse_query`.
        extra_title: Value of ``--title`` CLI flag (merged with ``filters``).
        extra_author: Value of ``--author`` CLI flag (merged with ``filters``).

    Returns:
        A query string suitable for arXiv ``search_query`` parameter.
    """
    merged = dict(filters)
    if extra_title:
        merged["title"] = extra_title
    if extra_author:
        merged["author"] = extra_author

    parts: list[str] = []

    if base:
        parts.append(f"all:{base}")

    for field, value in merged.items():
        prefix = _ARXIV_FIELD.get(field)
        if prefix:
            parts.append(f"{prefix}:{value}")
        else:
            # Unknown field — fold into full-text search.
            parts.append(f"all:{value}")

    return " AND ".join(parts) if parts else "all:"


# ---------------------------------------------------------------------------
# Semantic Scholar query builder
# ---------------------------------------------------------------------------


def build_ss_query(
    base: str,
    filters: dict[str, str],
    *,
    extra_title: str | None = None,
    extra_author: str | None = None,
) -> str:
    """Build a Semantic Scholar keyword query.

    SS does not support structured field queries; all terms are folded into
    a single keyword string.  Title and author hints are appended verbatim
    so the search engine can weight them naturally.

    Args:
        base: Free-text keywords.
        filters: Field-value dict from :func:`parse_query`.
        extra_title: Value of ``--title`` CLI flag.
        extra_author: Value of ``--author`` CLI flag.

    Returns:
        A plain keyword query string for the SS ``/paper/search`` endpoint.
    """
    merged = dict(filters)
    if extra_title:
        merged["title"] = extra_title
    if extra_author:
        merged["author"] = extra_author

    parts = [base] if base else []
    parts.extend(v for v in merged.values() if v)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Year-range helpers
# ---------------------------------------------------------------------------


def ss_year_param(year_from: int | None, year_to: int | None) -> str | None:
    """Return the SS ``year`` query parameter string, or None if no filter."""
    if year_from and year_to:
        return f"{year_from}-{year_to}"
    if year_from:
        return f"{year_from}-"
    if year_to:
        return f"-{year_to}"
    return None


def in_year_range(year: int | None, year_from: int | None, year_to: int | None) -> bool:
    """Return True if *year* falls within [year_from, year_to].

    None bounds are treated as open-ended.  A paper with no year always
    passes (avoid over-filtering incomplete metadata).
    """
    if year is None:
        return True
    if year_from is not None and year < year_from:
        return False
    return not (year_to is not None and year > year_to)


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------


def cache_key(
    source: str,
    query: str,
    max_results: int,
    sort: str,
    year_from: int | None = None,
    year_to: int | None = None,
) -> str:
    """Return a stable, compact cache key for a search request.

    The key is a short SHA-256 hex digest of the serialised parameters,
    prefixed with ``search:{source}:`` for readability.

    Args:
        source: Source name, e.g. ``"arxiv"``.
        query: Fully-built query string for this source.
        max_results: Result limit sent to the API.
        sort: Sort criterion string.
        year_from: Optional lower year bound.
        year_to: Optional upper year bound.

    Returns:
        A string like ``"search:arxiv:a3f2c1d4"``.
    """
    raw = f"{source}|{query}|{max_results}|{sort}|{year_from}|{year_to}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"search:{source}:{digest}"
