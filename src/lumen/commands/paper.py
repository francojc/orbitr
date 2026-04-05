"""lumen paper / lumen cite — fetch a paper or its citations by ID."""

from __future__ import annotations

from typing import Annotated

import typer

from lumen.config import VALID_FORMATS


def paper(
    ctx: typer.Context,
    paper_id: Annotated[
        str, typer.Argument(help="Paper ID (arXiv ID, DOI, or Semantic Scholar ID).")
    ],
    fmt: Annotated[
        str | None,
        typer.Option(
            "--format", "-f", help=f"Output format. ({', '.join(VALID_FORMATS)})"
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the local paper cache."),
    ] = False,
) -> None:
    """Fetch full details for a single paper by ID.

    Accepts arXiv IDs (e.g. 1706.03762), DOIs, or Semantic Scholar paper IDs.
    Displays title, authors, abstract, venue, citation count, and links.

    Examples:

      lumen paper 1706.03762

      lumen paper 10.18653/v1/2020.acl-main.196

      lumen paper 1706.03762 --format json
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] paper: {paper_id!r}")
    raise typer.Exit()


def cite(
    ctx: typer.Context,
    paper_id: Annotated[
        str, typer.Argument(help="Paper ID whose citations to retrieve.")
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of citing papers to return.",
            min=1,
            max=200,
        ),
    ] = 10,
    fmt: Annotated[
        str | None,
        typer.Option(
            "--format", "-f", help=f"Output format. ({', '.join(VALID_FORMATS)})"
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the local citation cache."),
    ] = False,
) -> None:
    """List papers that cite a given paper (via Semantic Scholar).

    Examples:

      lumen cite 1706.03762

      lumen cite 1706.03762 --limit 50 --format json
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] cite: {paper_id!r} (limit={limit})")
    raise typer.Exit()
