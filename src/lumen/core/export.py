"""Bibliography export formatters: BibTeX, RIS, CSL-JSON.

All formatters accept a list[Paper] and return a formatted string
suitable for stdout or file output.
"""

from __future__ import annotations

from typing import Literal

from lumen.core.models import Paper

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


def to_bibtex(papers: list[Paper]) -> str:
    """Render papers as BibTeX entries.

    Args:
        papers: Papers to format.

    Returns:
        BibTeX string with one entry per paper.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError


def to_ris(papers: list[Paper]) -> str:
    """Render papers in RIS format.

    Args:
        papers: Papers to format.

    Returns:
        RIS-formatted string with one record per paper.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError


def to_csl_json(papers: list[Paper]) -> str:
    """Render papers as a CSL-JSON array.

    Args:
        papers: Papers to format.

    Returns:
        JSON string containing a CSL-JSON array.
    """
    # TODO: implement in Phase 2
    raise NotImplementedError


def _bibtex_key(paper: Paper) -> str:
    """Generate a BibTeX citation key from author surname and year.

    Args:
        paper: Source paper.

    Returns:
        Citation key string, e.g. "Vaswani2017".
    """
    surname = paper.authors[0].name.split()[-1] if paper.authors else "Unknown"
    year = str(paper.year) if paper.year else "XXXX"
    return f"{surname}{year}"
