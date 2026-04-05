"""JSON serialiser — newline-delimited (ndjson), pipe-friendly output."""

from __future__ import annotations

import sys
from typing import IO

from lumen.core.models import Paper


def render_json(papers: list[Paper], file: IO[str] | None = None) -> None:
    """Write papers as newline-delimited JSON to a file-like object.

    Each line is a complete, valid JSON object representing one paper.
    Safe to pipe to ``jq``, ``lumen export``, or any ndjson-aware tool.

    Args:
        papers: Papers to serialise.
        file: Output stream (default: sys.stdout).
    """
    out = file or sys.stdout
    for paper in papers:
        out.write(paper.model_dump_json())
        out.write("\n")
