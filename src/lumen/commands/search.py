"""lumen search — keyword and field-filtered search across sources."""

from __future__ import annotations

from typing import Annotated

import typer

from lumen.config import VALID_FORMATS, VALID_SOURCES


def search(
    ctx: typer.Context,
    query: Annotated[
        str, typer.Argument(help="Search query (keywords or field:value syntax).")
    ],
    sources: Annotated[
        str | None,
        typer.Option(
            "--sources",
            "-s",
            help=f"Comma-separated sources to query. ({', '.join(VALID_SOURCES)})",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit", "-n", help="Maximum number of results to return.", min=1, max=200
        ),
    ] = 10,
    title: Annotated[
        str | None,
        typer.Option("--title", "-T", help="Filter by title keywords."),
    ] = None,
    author: Annotated[
        str | None,
        typer.Option("--author", "-a", help="Filter by author name."),
    ] = None,
    venue: Annotated[
        str | None,
        typer.Option("--venue", "-j", help="Filter by journal or conference name."),
    ] = None,
    year_from: Annotated[
        int | None,
        typer.Option("--from", help="Include papers published on or after this year."),
    ] = None,
    year_to: Annotated[
        int | None,
        typer.Option("--to", help="Include papers published on or before this year."),
    ] = None,
    sort: Annotated[
        str,
        typer.Option(
            "--sort",
            help="Sort criterion: relevance, citations, date, impact, combined.",
        ),
    ] = "relevance",
    fmt: Annotated[
        str | None,
        typer.Option(
            "--format", "-f", help=f"Output format. ({', '.join(VALID_FORMATS)})"
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the local result cache."),
    ] = False,
) -> None:
    """Search academic literature across arXiv and Semantic Scholar.

    Queries are run concurrently across all enabled sources. Results are
    deduplicated by DOI, arXiv ID, and fuzzy title matching, then ranked
    by the chosen sort criterion.

    Examples:

      lumen search "transformer attention"

      lumen search "BERT" --sources semantic_scholar --limit 20

      lumen search "neural machine translation" --author "Vaswani" --from 2017

      lumen search "title:contrastive learning" --sort citations --format json
    """
    # TODO: implement in Phase 3
    typer.echo(f"[stub] search: {query!r} (sources={sources}, limit={limit})")
    raise typer.Exit()
