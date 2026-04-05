"""Rich Panel/group renderer for labelled-block paper listings."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from lumen.core.models import Paper

_ABSTRACT_MAX = 200


def _abstract_snippet(paper: Paper) -> str:
    """Return the first *_ABSTRACT_MAX* characters of the abstract."""
    if not paper.abstract:
        return ""
    text = paper.abstract.strip().replace("\n", " ")
    if len(text) <= _ABSTRACT_MAX:
        return text
    return text[: _ABSTRACT_MAX - 1] + "…"


def _meta_line(paper: Paper) -> Text:
    """Build a compact metadata line: authors · venue · year · source."""
    t = Text()

    authors = paper.author_names
    if authors:
        first = authors[0].split()[-1]
        author_str = first if len(authors) == 1 else f"{first} et al. ({len(authors)})"
        t.append(author_str, style="cyan")
        t.append("  ·  ", style="dim")

    if paper.venue:
        t.append(paper.venue[:40], style="italic")
        t.append("  ·  ", style="dim")

    if paper.year:
        t.append(str(paper.year), style="yellow")
        t.append("  ·  ", style="dim")

    _SOURCE_LABELS = {"semantic_scholar": "Sem. Scholar", "arxiv": "arXiv"}
    t.append(
        _SOURCE_LABELS.get(paper.source, paper.source.replace("_", " ")), style="dim"
    )

    if paper.citation_count is not None:
        t.append("  ·  ", style="dim")
        t.append(f"{paper.citation_count} cites", style="dim")

    return t


def render_list(papers: list[Paper], console: Console | None = None) -> None:
    """Render papers as labelled Rich Panels — one block per paper.

    Shows title, authors, venue/year, abstract snippet, and source URL.

    Args:
        papers: Papers to display.
        console: Rich Console to render into. Creates a default one if None.
    """
    con = console or Console()

    if not papers:
        con.print("[dim]No results.[/dim]")
        return

    for idx, paper in enumerate(papers, start=1):
        body = Text()

        meta = _meta_line(paper)
        body.append_text(meta)

        snippet = _abstract_snippet(paper)
        if snippet:
            body.append("\n")
            body.append(snippet, style="dim")

        body.append("\n")
        body.append(paper.url, style="blue underline")

        panel = Panel(
            body,
            title=f"[bold]{idx}. {paper.title}[/bold]",
            title_align="left",
            border_style="dim",
            padding=(0, 1),
        )
        con.print(panel)
