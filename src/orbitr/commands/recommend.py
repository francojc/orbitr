"""orbitr recommend — paper recommendations from a seed paper ID."""

from __future__ import annotations

import json
import logging
from typing import Annotated

import typer
from rich.console import Console

from orbitr._async import run
from orbitr.clients.semantic_scholar import SemanticScholarClient
from orbitr.commands.paper import _detect_id_type, _normalize_for_ss
from orbitr.config import VALID_FORMATS
from orbitr.core.cache import Cache
from orbitr.core.models import Paper
from orbitr.display import Format, effective_format, render
from orbitr.exceptions import LumenError, NoResultsError, SourceError

logger = logging.getLogger(__name__)

_err = Console(stderr=True)

RECOMMEND_METHODS = ("content", "citation", "hybrid")


def recommend(
    ctx: typer.Context,
    seed: Annotated[
        str,
        typer.Argument(help="Seed paper ID (arXiv ID, DOI, or Semantic Scholar ID)."),
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
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Bypass the local cache."),
    ] = False,
) -> None:
    """Recommend papers similar to a seed paper.

    Uses Semantic Scholar's recommendation API. The --method flag is
    accepted for forward compatibility; all methods currently use the
    same underlying endpoint.

    Examples:

      orbitr recommend 1706.03762

      orbitr recommend 1706.03762 --limit 20 --format json
    """
    cfg = ctx.obj.config
    effective_fmt = effective_format(fmt, cfg.format)

    if effective_fmt not in VALID_FORMATS:
        _err.print(
            f"[red]Error:[/red] Unknown format {effective_fmt!r}. "
            f"Choose: {', '.join(VALID_FORMATS)}"
        )
        raise typer.Exit(code=2)

    if method not in RECOMMEND_METHODS:
        _err.print(
            f"[red]Error:[/red] Invalid method {method!r}. "
            f"Choose: {', '.join(RECOMMEND_METHODS)}"
        )
        raise typer.Exit(code=2)

    try:
        run(
            _recommend_async(
                seed=seed,
                limit=limit,
                fmt=effective_fmt,
                no_cache=no_cache or cfg.no_cache,
                cfg=cfg,
            )
        )
    except NoResultsError as exc:
        if not cfg.quiet:
            Console(no_color=cfg.no_color).print(
                f"[yellow]No recommendations found.[/yellow] {exc.suggestion}"
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


async def _recommend_async(
    *, seed: str, limit: int, fmt: Format, no_cache: bool, cfg
) -> None:
    """Fetch recommendations via Semantic Scholar and render them."""
    id_type = _detect_id_type(seed)
    ss_id = _normalize_for_ss(seed, id_type)
    cache_key = f"recommend:{ss_id}:{limit}"
    cache = Cache(cfg.cache_dir / "cache.db")

    papers: list[Paper]

    # Cache read
    if not no_cache:
        cached = cache.get(cache_key, "search")
        if cached is not None:
            try:
                papers = [Paper.model_validate(p) for p in cached]
                if not papers:
                    raise NoResultsError(
                        f"No recommendations found for '{seed}'.",
                        suggestion="Try a different seed paper ID.",
                    )
                import sys

                console = Console(no_color=cfg.no_color)
                pager = sys.stdout.isatty() and not cfg.no_pager
                render(papers, fmt=fmt, console=console, pager=pager)
                return
            except NoResultsError:
                raise
            except Exception:
                logger.debug("Cache entry corrupt for %s; refetching.", cache_key)

    # Live fetch — recommendations only via Semantic Scholar
    api_key = cfg.credentials.semantic_scholar_api_key
    client = SemanticScholarClient(api_key=api_key)
    papers = await client.get_recommendations(ss_id, limit=limit)

    # Cache write
    if not no_cache:
        cache.set(
            cache_key,
            [json.loads(p.model_dump_json()) for p in papers],
            "search",
        )

    if not papers:
        raise NoResultsError(
            f"No recommendations found for '{seed}'.",
            suggestion="Try a different seed paper or verify it exists on Semantic Scholar.",
        )

    import sys

    console = Console(no_color=cfg.no_color)
    pager = sys.stdout.isatty() and not cfg.no_pager
    render(papers[:limit], fmt=fmt, console=console, pager=pager)
