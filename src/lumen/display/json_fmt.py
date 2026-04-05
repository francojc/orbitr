"""JSON serialiser — newline-delimited, pipe-friendly output."""

from __future__ import annotations

from lumen.core.models import Paper


def render_json(papers: list[Paper], file=None) -> None:
    """Write papers as newline-delimited JSON to a file-like object.

    Each line is a valid JSON object representing one paper. Safe to pipe
    to `jq`, `lumen export`, or any other tool that reads ndjson.

    Args:
        papers: Papers to serialise.
        file: Output stream (default: sys.stdout).
    """
    # TODO: implement in Phase 4
    raise NotImplementedError
