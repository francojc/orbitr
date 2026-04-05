"""Rich Table renderer for search result lists."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from lumen.core.models import Paper

_TITLE_MAX = 52
_AUTHOR_MAX = 28


def _truncate(value: str, max_len: int) -> str:
    """Truncate *value* to *max_len* characters, appending '…' if cut."""
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def _format_authors(paper: Paper) -> str:
    """Return a compact author string: first author + count if multiple."""
    names = paper.author_names
    if not names:
        return "—"
    first = names[0].split()[-1]  # surname only
    if len(names) == 1:
        return names[0]
    return f"{first} et al. ({len(names)})"


def render_table(papers: list[Paper], console: Console | None = None) -> None:
    """Render papers as a Rich Table with truncated fields.

    Columns: #, Title, Authors, Year, Source, Citations.

    Args:
        papers: Papers to display.
        console: Rich Console to render into. Creates a default one if None.
    """
    con = console or Console()

    table = Table(
        show_header=True,
        header_style="bold",
        show_lines=False,
        expand=False,
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Title", min_width=20, max_width=_TITLE_MAX + 2)
    table.add_column("Authors", min_width=14, max_width=_AUTHOR_MAX + 2)
    table.add_column("Year", width=6, justify="right")
    table.add_column("Source", width=13)
    table.add_column("Cites", width=7, justify="right")

    for idx, paper in enumerate(papers, start=1):
        year = str(paper.year) if paper.year else "—"
        cites = str(paper.citation_count) if paper.citation_count is not None else "—"
        _SOURCE_LABELS = {"semantic_scholar": "Sem. Scholar", "arxiv": "arXiv"}
        source_label = _SOURCE_LABELS.get(paper.source, paper.source.replace("_", " "))

        table.add_row(
            str(idx),
            _truncate(paper.title, _TITLE_MAX),
            _truncate(_format_authors(paper), _AUTHOR_MAX),
            year,
            source_label,
            cites,
        )

    if not papers:
        con.print("[dim]No results.[/dim]")
        return

    con.print(table)
