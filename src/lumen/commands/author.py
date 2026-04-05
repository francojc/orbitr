"""lumen author — search for authors and list their papers."""

from __future__ import annotations

from typing import Annotated

import typer

from lumen.config import VALID_FORMATS


def author(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Author name to search for.")],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of papers to list per author.",
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
) -> None:
    """Search for an author and list their most-cited papers.

    Queries Semantic Scholar's author search endpoint. Returns author
    profile information and a ranked list of their publications.

    Examples:

      lumen author "Yoshua Bengio"

      lumen author "LeCun" --limit 20 --format json
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] author: {name!r} (limit={limit})")
    raise typer.Exit()
