"""Rich display renderers: table, list, detail, json.

Public entry point
------------------
Use :func:`render` to dispatch to the appropriate renderer based on the
format string.  Individual renderers (``render_table``, ``render_list``,
``render_json``) can also be imported directly when needed.
"""

from __future__ import annotations

import sys
from typing import IO, Literal

from rich.console import Console

from lumen.core.models import Paper

from .json_fmt import render_json
from .list import render_list
from .table import render_table

__all__ = [
    "render",
    "render_table",
    "render_list",
    "render_json",
]

Format = Literal["table", "list", "detail", "json"]


def render(
    papers: list[Paper],
    fmt: Format = "table",
    *,
    console: Console | None = None,
    file: IO[str] | None = None,
) -> None:
    """Dispatch to the appropriate renderer.

    Args:
        papers: Papers to display.
        fmt: One of ``"table"``, ``"list"``, ``"detail"``, ``"json"``.
        console: Rich Console (used for table/list/detail formats).
        file: Output stream (used for json format; defaults to stdout).

    Raises:
        ValueError: If *fmt* is not a recognised format string.
    """
    if fmt == "table":
        render_table(papers, console=console)
    elif fmt == "list":
        render_list(papers, console=console)
    elif fmt == "json":
        render_json(papers, file=file or sys.stdout)
    elif fmt == "detail":
        # Phase 4: full single-paper detail view.  For now fall back to list.
        render_list(papers, console=console)
    else:
        raise ValueError(
            f"Unknown format: {fmt!r}. Choose table, list, detail, or json."
        )
