"""Bibliography export formatters: BibTeX, RIS, CSL-JSON.

All formatters accept a list[Paper] and return a formatted string
suitable for stdout or file output.
"""

from __future__ import annotations

import json as _json
import re
from typing import Literal

from orbitr.core.models import Paper

ExportFormat = Literal["bibtex", "ris", "csl-json"]


def export(papers: list[Paper], fmt: ExportFormat) -> str:
    """Format a list of papers as a bibliography string.

    Args:
        papers: Papers to export.
        fmt: Target bibliography format.

    Returns:
        Formatted string in the requested format.

    Raises:
        ValueError: If fmt is not a supported format.
    """
    dispatch = {
        "bibtex": to_bibtex,
        "ris": to_ris,
        "csl-json": to_csl_json,
    }
    if fmt not in dispatch:
        raise ValueError(
            f"Unsupported export format: {fmt!r}. Choose from {list(dispatch)}"
        )
    return dispatch[fmt](papers)


# ---------------------------------------------------------------------------
# BibTeX
# ---------------------------------------------------------------------------

_BIBTEX_SPECIAL = re.compile(r"[\\{}]")


def _bibtex_escape(text: str) -> str:
    """Escape backslashes and braces in a BibTeX field value."""
    return _BIBTEX_SPECIAL.sub(lambda m: "\\" + m.group(), text)


def _bibtex_key(paper: Paper) -> str:
    """Generate a BibTeX citation key from author surname and year.

    Args:
        paper: Source paper.

    Returns:
        Citation key string, e.g. ``Vaswani2017``.
    """
    surname = paper.authors[0].name.split()[-1] if paper.authors else "Unknown"
    # Strip non-alphanumeric characters from the surname
    surname = re.sub(r"[^A-Za-z0-9]", "", surname) or "Unknown"
    year = str(paper.year) if paper.year else "XXXX"
    return f"{surname}{year}"


def to_bibtex(papers: list[Paper]) -> str:
    """Render papers as BibTeX entries.

    Uses ``@article`` type for all papers (suitable for preprints and
    journal articles alike).

    Args:
        papers: Papers to format.

    Returns:
        BibTeX string with one ``@article`` entry per paper, separated
        by blank lines and terminated with a trailing newline.
    """
    entries: list[str] = []

    for paper in papers:
        key = _bibtex_key(paper)
        lines: list[str] = [f"@article{{{key},"]

        lines.append(f"  title     = {{{_bibtex_escape(paper.title)}}},")

        if paper.authors:
            joined = " and ".join(a.name for a in paper.authors)
            lines.append(f"  author    = {{{joined}}},")

        if paper.year:
            lines.append(f"  year      = {{{paper.year}}},")

        if paper.venue:
            lines.append(f"  journal   = {{{_bibtex_escape(paper.venue)}}},")

        if paper.doi:
            lines.append(f"  doi       = {{{paper.doi}}},")

        if paper.url:
            lines.append(f"  url       = {{{paper.url}}},")

        if paper.abstract:
            lines.append(f"  abstract  = {{{_bibtex_escape(paper.abstract)}}},")

        lines.append("}")
        entries.append("\n".join(lines))

    return ("\n\n".join(entries) + "\n") if entries else ""


# ---------------------------------------------------------------------------
# RIS
# ---------------------------------------------------------------------------


def to_ris(papers: list[Paper]) -> str:
    """Render papers in RIS format.

    Uses ``TY  - JOUR`` for all papers. Each record is terminated with
    ``ER  -`` and separated by a blank line.

    Args:
        papers: Papers to format.

    Returns:
        RIS-formatted string with one record per paper.
    """
    records: list[str] = []

    for paper in papers:
        lines: list[str] = ["TY  - JOUR"]

        lines.append(f"TI  - {paper.title}")

        for a in paper.authors:
            lines.append(f"AU  - {a.name}")

        if paper.year:
            lines.append(f"PY  - {paper.year}")

        if paper.venue:
            lines.append(f"JO  - {paper.venue}")

        if paper.doi:
            lines.append(f"DO  - {paper.doi}")

        if paper.url:
            lines.append(f"UR  - {paper.url}")

        if paper.abstract:
            lines.append(f"AB  - {paper.abstract}")

        lines.append("ER  -")
        records.append("\n".join(lines))

    return ("\n\n".join(records) + "\n") if records else ""


# ---------------------------------------------------------------------------
# CSL-JSON
# ---------------------------------------------------------------------------


def _csl_author(name: str) -> dict:
    """Split a full name into CSL ``given`` / ``family`` fields.

    Falls back to ``literal`` when the name cannot be split.
    """
    parts = name.strip().rsplit(" ", 1)
    if len(parts) == 2:
        return {"given": parts[0], "family": parts[1]}
    return {"literal": name}


def to_csl_json(papers: list[Paper]) -> str:
    """Render papers as a CSL-JSON array.

    Produces a JSON array suitable for use with Pandoc, Zotero, and
    other CSL-aware tools.

    Args:
        papers: Papers to format.

    Returns:
        JSON string containing a CSL-JSON array, terminated with a
        trailing newline.
    """
    items: list[dict] = []

    for paper in papers:
        item: dict = {
            "id": _bibtex_key(paper),
            "type": "article-journal",
            "title": paper.title,
        }

        if paper.authors:
            item["author"] = [_csl_author(a.name) for a in paper.authors]

        if paper.year:
            item["issued"] = {"date-parts": [[paper.year]]}

        if paper.doi:
            item["DOI"] = paper.doi

        if paper.url:
            item["URL"] = paper.url

        if paper.venue:
            item["container-title"] = paper.venue

        if paper.abstract:
            item["abstract"] = paper.abstract

        items.append(item)

    return _json.dumps(items, indent=2, ensure_ascii=False) + "\n"
