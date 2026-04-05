"""Rich Panel/group renderer for labelled-block paper listings."""

from __future__ import annotations

from rich.console import Console

from lumen.core.models import Paper


def render_list(papers: list[Paper], console: Console | None = None) -> None:
    """Render papers as labelled Rich Panels — one block per paper.

    Shows title, authors, venue/year, abstract snippet, and source URL.

    Args:
        papers: Papers to display.
        console: Rich Console to render into. Creates a default one if None.
    """
    # TODO: implement in Phase 4
    raise NotImplementedError
