"""Full single-paper detail renderer using Rich layout primitives."""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from lumen.core.models import Paper

_SOURCE_LABELS: dict[str, str] = {
    "arxiv": "arXiv",
    "semantic_scholar": "Semantic Scholar",
}

_SOURCE_STYLES: dict[str, str] = {
    "arxiv": "bold red",
    "semantic_scholar": "bold cyan",
}


def _source_badge(paper: Paper) -> Text:
    """Return a styled source badge."""
    label = _SOURCE_LABELS.get(paper.source, paper.source.replace("_", " ").title())
    style = _SOURCE_STYLES.get(paper.source, "bold white")
    return Text(f"[{label}]", style=style)


def _authors_block(paper: Paper) -> Text:
    """Build a multi-line authors block with affiliations where available."""
    if not paper.authors:
        return Text("Unknown authors", style="dim italic")

    t = Text()
    for i, author in enumerate(paper.authors):
        t.append(author.name, style="cyan")
        if author.affiliation:
            t.append(f"  ({author.affiliation})", style="dim")
        if i < len(paper.authors) - 1:
            t.append("\n")
    return t


def _meta_table(paper: Paper) -> Table:
    """Build a two-column key/value metadata table."""
    tbl = Table.grid(padding=(0, 2))
    tbl.add_column(style="dim", justify="right")
    tbl.add_column()

    if paper.year:
        tbl.add_row("Year", str(paper.year))
    if paper.venue:
        tbl.add_row("Venue", paper.venue)
    if paper.categories:
        tbl.add_row("Categories", "  ·  ".join(paper.categories))
    if paper.citation_count is not None:
        tbl.add_row("Citations", str(paper.citation_count))
    if paper.doi:
        tbl.add_row("DOI", Text(paper.doi, style="blue"))
    if paper.arxiv_id:
        tbl.add_row("arXiv ID", Text(paper.arxiv_id, style="blue"))

    return tbl


def _links_block(paper: Paper) -> Text:
    """Build a compact links line."""
    t = Text()
    t.append("URL  ", style="dim")
    t.append(paper.url, style="blue underline")
    if paper.pdf_url:
        t.append("    PDF  ", style="dim")
        t.append(paper.pdf_url, style="blue underline")
    return t


def _abstract_panel(paper: Paper) -> Panel | Text:
    """Return the abstract wrapped in a panel, or a dim placeholder."""
    if not paper.abstract:
        return Text("No abstract available.", style="dim italic")
    text = paper.abstract.strip().replace("\n", " ")
    return Panel(
        Text(text, style="default"),
        title="Abstract",
        title_align="left",
        border_style="dim",
        padding=(0, 1),
    )


def render_detail(papers: list[Paper], console: Console | None = None) -> None:
    """Render one or more papers in full detail view.

    Displays all available fields per paper: title, source badge, authors
    with affiliations, full abstract, metadata (year, venue, categories,
    citation count, DOI, arXiv ID), and links (URL, PDF).

    When multiple papers are passed each is separated by a Rule.

    Args:
        papers: Papers to display.
        console: Rich Console to render into. Creates a default one if None.
    """
    con = console or Console()

    if not papers:
        con.print("[dim]No results.[/dim]")
        return

    for idx, paper in enumerate(papers):
        if idx > 0:
            con.print(Rule(style="dim"))

        # --- Title + source badge -------------------------------------------
        title_text = Text()
        title_text.append(paper.title, style="bold white")
        badge = _source_badge(paper)
        header = Columns([title_text, badge], expand=False, align="left")
        con.print(header)
        con.print()

        # --- Authors -----------------------------------------------------------
        con.print(_authors_block(paper))
        con.print()

        # --- Abstract ----------------------------------------------------------
        con.print(_abstract_panel(paper))
        con.print()

        # --- Metadata ----------------------------------------------------------
        meta = _meta_table(paper)
        if meta.row_count:
            con.print(meta)
            con.print()

        # --- Links -------------------------------------------------------------
        con.print(_links_block(paper))
