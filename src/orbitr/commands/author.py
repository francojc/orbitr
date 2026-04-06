"""orbitr author — search for an author and list their papers."""

from __future__ import annotations

import json
import logging
from typing import Annotated

import typer
from rich.console import Console

from orbitr._async import run
from orbitr.clients.semantic_scholar import SemanticScholarClient
from orbitr.config import VALID_FORMATS
from orbitr.core.cache import Cache
from orbitr.core.models import Paper
from orbitr.display import Format, effective_format, render
from orbitr.exceptions import LumenError, NoResultsError, SourceError

logger = logging.getLogger(__name__)

_err = Console(stderr=True)


def author(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Author name to search for.")],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of papers to list.",
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
        typer.Option("--no-cache", help="Bypass the local cache."),
    ] = False,
) -> None:
    """Search for an author and list their most-cited papers.

    Queries Semantic Scholar's author search endpoint. Returns a ranked
    list of publications from the best-matching author.

    Examples:

      orbitr author "Yoshua Bengio"

      orbitr author "LeCun" --limit 20 --format json
    """
    cfg = ctx.obj.config
    effective_fmt = effective_format(fmt, cfg.format)

    if effective_fmt not in VALID_FORMATS:
        _err.print(
            f"[red]Error:[/red] Unknown format {effective_fmt!r}. "
            f"Choose: {', '.join(VALID_FORMATS)}"
        )
        raise typer.Exit(code=2)

    try:
        run(
            _author_async(
                name=name,
                limit=limit,
                fmt=effective_fmt,
                no_cache=no_cache or cfg.no_cache,
                cfg=cfg,
            )
        )
    except NoResultsError as exc:
        if not cfg.quiet:
            Console(no_color=cfg.no_color).print(
                f"[yellow]No papers found.[/yellow] {exc.suggestion}"
            )
        raise typer.Exit(code=4) from None
    except SourceError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(f"[dim]{exc.suggestion}[/dim]")
        raise typer.Exit(code=1) from exc
    except LumenError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(f"[dim]{exc.suggestion}[/dim]")
        raise typer.Exit(code=1) from exc


async def _author_async(
    *, name: str, limit: int, fmt: Format, no_cache: bool, cfg
) -> None:
    """Fetch an author's papers via Semantic Scholar and render them."""
    cache_key = f"author:{name.lower()}:{limit}"
    cache = Cache(cfg.cache_dir / "cache.db")

    papers: list[Paper]

    # Cache read
    if not no_cache:
        cached = cache.get(cache_key, "search")
        if cached is not None:
            try:
                papers = [Paper.model_validate(p) for p in cached]
                if papers:
                    import sys

                    console = Console(no_color=cfg.no_color)
                    pager = sys.stdout.isatty() and not cfg.no_pager
                    render(papers, fmt=fmt, console=console, pager=pager)
                    return
            except Exception:
                logger.debug("Cache entry corrupt for %s; refetching.", cache_key)

    # Live fetch
    api_key = cfg.credentials.semantic_scholar_api_key
    client = SemanticScholarClient(api_key=api_key)
    papers = await client.search_authors(name, limit=limit)

    # Cache write
    if not no_cache:
        cache.set(
            cache_key,
            [json.loads(p.model_dump_json()) for p in papers],
            "search",
        )

    if not papers:
        raise NoResultsError(
            f"No papers found for author '{name}'.",
            suggestion="Try a different spelling or use a surname only.",
        )

    import sys

    console = Console(no_color=cfg.no_color)
    pager = sys.stdout.isatty() and not cfg.no_pager
    render(papers[:limit], fmt=fmt, console=console, pager=pager)
