"""Rich display renderers: table, list, detail, json.

Public entry point
------------------
Use :func:`render` to dispatch to the appropriate renderer based on the
format string.  Individual renderers (``render_table``, ``render_list``,
``render_detail``, ``render_json``) can also be imported directly when needed.

TTY detection
-------------
Use :func:`effective_format` instead of ``fmt or cfg.format`` in commands.
It auto-switches the default to ``"json"`` when stdout is not a TTY so that
piped output is always machine-readable without requiring an explicit flag.

Pager
-----
Pass ``pager=True`` to :func:`render` to route Rich output through the
terminal pager (``$PAGER``, defaulting to ``less -R``).  Paging is skipped
for the ``"json"`` format (JSON consumers handle their own paging) and
when stdout is not a TTY.
"""

from __future__ import annotations

import sys
from typing import IO, Literal

from rich.console import Console

from orbitr.core.models import Paper

from .detail import render_detail
from .json_fmt import render_json
from .panels import render_list
from .table import render_table

__all__ = [
    "render",
    "effective_format",
    "render_table",
    "render_list",
    "render_detail",
    "render_json",
]

Format = Literal["table", "list", "detail", "json"]


def effective_format(explicit: str | None, default: str) -> str:
    """Return the output format to use, with automatic TTY detection.

    Resolution order:
      1. ``explicit`` — honours an explicit ``--format`` flag.
      2. ``"json"`` — when stdout is not a TTY (pipe / redirect), so that
         output is always machine-readable without requiring a flag.
      3. ``default`` — the configured or built-in default (``"table"``
         for interactive sessions).

    Args:
        explicit: Value passed to ``--format``, or ``None`` if omitted.
        default: Format from config (``cfg.format``).

    Returns:
        Format string to pass to :func:`render`.
    """
    if explicit is not None:
        return explicit
    if not sys.stdout.isatty():
        return "json"
    return default


def _render_rich(papers: list[Paper], fmt: str, console: Console) -> None:
    """Dispatch to the appropriate Rich renderer (non-JSON formats only)."""
    if fmt == "table":
        render_table(papers, console=console)
    elif fmt == "list":
        render_list(papers, console=console)
    elif fmt == "detail":
        render_detail(papers, console=console)
    else:
        raise ValueError(
            f"Unknown format: {fmt!r}. Choose table, list, detail, or json."
        )


def render(
    papers: list[Paper],
    fmt: Format = "table",
    *,
    console: Console | None = None,
    file: IO[str] | None = None,
    pager: bool = False,
) -> None:
    """Dispatch to the appropriate renderer.

    Args:
        papers: Papers to display.
        fmt: One of ``"table"``, ``"list"``, ``"detail"``, ``"json"``.
        console: Rich Console (used for table/list/detail formats).
        file: Output stream (used for json format; defaults to stdout).
        pager: When ``True`` and *fmt* is not ``"json"``, route Rich output
            through the terminal pager (``$PAGER`` or ``less -R``).
            Ignored when stdout is not a TTY.

    Raises:
        ValueError: If *fmt* is not a recognised format string.
    """
    if fmt == "json":
        render_json(papers, file=file or sys.stdout)
        return

    con = console or Console()

    if pager and sys.stdout.isatty():
        with con.pager(styles=True):
            _render_rich(papers, fmt, con)
    else:
        _render_rich(papers, fmt, con)
