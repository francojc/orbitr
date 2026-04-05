"""lumen recommend — paper recommendations from a seed title or ID."""

from __future__ import annotations

from typing import Annotated

import typer

from lumen.config import VALID_FORMATS

RECOMMEND_METHODS = ("content", "citation", "hybrid")


def recommend(
    ctx: typer.Context,
    seed: Annotated[
        str, typer.Argument(help="Seed paper ID (arXiv ID, DOI) or quoted title.")
    ],
    method: Annotated[
        str,
        typer.Option(
            "--method",
            "-m",
            help=f"Recommendation method. ({', '.join(RECOMMEND_METHODS)})",
        ),
    ] = "hybrid",
    limit: Annotated[
        int,
        typer.Option(
            "--limit", "-n", help="Number of recommendations to return.", min=1, max=50
        ),
    ] = 10,
    fmt: Annotated[
        str | None,
        typer.Option(
            "--format", "-f", help=f"Output format. ({', '.join(VALID_FORMATS)})"
        ),
    ] = None,
) -> None:
    """Recommend papers similar to a seed paper.

    Uses Semantic Scholar's recommendation API. Three methods are
    available: content-based (abstract similarity), citation-based
    (shared references/citations), or hybrid (weighted combination).

    Examples:

      lumen recommend 1706.03762

      lumen recommend "Attention is All You Need" --method citation

      lumen recommend 1706.03762 --limit 20 --format json
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] recommend: {seed!r} (method={method}, limit={limit})")
    raise typer.Exit()
