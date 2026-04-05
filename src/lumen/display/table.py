"""Rich Table renderer for search result lists."""

from __future__ import annotations

from rich.console import Console

from lumen.core.models import Paper


def render_table(papers: list[Paper], console: Console | None = None) -> None:
    """Render papers as a Rich Table with truncated fields.

    Columns: #, Title (truncated), Authors (first + count), Year, Source, Citations.

    Args:
        papers: Papers to display.
        console: Rich Console to render into. Creates a default one if None.
    """
    # TODO: implement in Phase 4
    raise NotImplementedError
