"""lumen search — keyword and field-filtered search across sources."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated

import typer
from rich.console import Console

from lumen._async import run
from lumen.clients.arxiv import ArxivClient
from lumen.clients.semantic_scholar import SemanticScholarClient
from lumen.config import VALID_FORMATS, VALID_SOURCES, Config
from lumen.core.cache import Cache
from lumen.core.deduplication import deduplicate
from lumen.core.models import Paper, SearchResult
from lumen.core.query import (
    build_arxiv_query,
    build_ss_query,
    cache_key,
    in_year_range,
    parse_query,
    ss_year_param,
)
from lumen.core.ranking import rank
from lumen.display import render
from lumen.exceptions import LumenError, NoResultsError, SourceError, UsageError

logger = logging.getLogger(__name__)

_err = Console(stderr=True)


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
    cfg: Config = ctx.obj.config

    # Validate --sort
    _valid_sorts = {"relevance", "citations", "date", "impact", "combined"}
    if sort not in _valid_sorts:
        _err.print(
            f"[red]Error:[/red] Unknown sort criterion {sort!r}. "
            f"Choose: {', '.join(sorted(_valid_sorts))}."
        )
        raise typer.Exit(code=2)

    # Validate --format
    effective_fmt = fmt or cfg.format
    if effective_fmt not in VALID_FORMATS:
        _err.print(
            f"[red]Error:[/red] Unknown format {effective_fmt!r}. "
            f"Choose: {', '.join(VALID_FORMATS)}."
        )
        raise typer.Exit(code=2)

    # Validate --sources
    source_list: list[str]
    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
        invalid = [s for s in source_list if s not in VALID_SOURCES]
        if invalid:
            _err.print(
                f"[red]Error:[/red] Unknown source(s): {', '.join(invalid)}. "
                f"Choose from: {', '.join(VALID_SOURCES)}."
            )
            raise typer.Exit(code=2)
    else:
        source_list = cfg.sources

    try:
        papers = run(
            _search_async(
                cfg=cfg,
                raw_query=query,
                sources=source_list,
                limit=limit,
                title=title,
                author=author,
                venue=venue,
                year_from=year_from,
                year_to=year_to,
                sort=sort,
                no_cache=no_cache or cfg.no_cache,
            )
        )
    except NoResultsError as exc:
        if not cfg.quiet:
            console = Console(no_color=cfg.no_color)
            console.print(f"[yellow]No results found.[/yellow] {exc.suggestion}")
        raise typer.Exit(code=4) from None
    except SourceError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(exc.suggestion)
        raise typer.Exit(code=1) from exc
    except UsageError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        if exc.suggestion:
            _err.print(exc.suggestion)
        raise typer.Exit(code=2) from exc
    except LumenError as exc:
        _err.print(f"[red]Error:[/red] {exc.message}")
        raise typer.Exit(code=1) from exc

    console = Console(no_color=cfg.no_color)
    render(papers, fmt=effective_fmt, console=console)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Async implementation
# ---------------------------------------------------------------------------


async def _fetch_source(
    source: str,
    query_str: str,
    limit: int,
    sort: str,
    year_from: int | None,
    year_to: int | None,
    cache: Cache,
    no_cache: bool,
    api_key: str,
) -> list[Paper]:
    """Fetch papers from one source, using the cache when available.

    Args:
        source: Source name (``"arxiv"`` or ``"semantic_scholar"``).
        query_str: Source-specific query string.
        limit: Maximum papers to request from the API.
        sort: Sort criterion (used in cache key only).
        year_from: Lower year bound for post-filtering.
        year_to: Upper year bound for post-filtering.
        cache: Cache instance shared across sources.
        no_cache: If True, skip cache read and write.
        api_key: API key for Semantic Scholar (unused for arXiv).

    Returns:
        List of ``Paper`` objects from this source.
    """
    key = cache_key(source, query_str, limit, sort, year_from, year_to)

    # --- Cache hit ---
    if not no_cache:
        cached = cache.get(key, "search")
        if cached is not None:
            logger.debug("Cache hit: %s", key)
            try:
                return [Paper.model_validate(p) for p in cached]
            except Exception:
                logger.debug("Cache entry corrupt for %s; refetching.", key)

    # --- Live fetch ---
    if source == "arxiv":
        client: ArxivClient | SemanticScholarClient = ArxivClient()
        result: SearchResult = await client.search(query_str, max_results=limit)
    elif source == "semantic_scholar":
        client = SemanticScholarClient(api_key=api_key)
        year_param = ss_year_param(year_from, year_to)
        extra_params = {"year": year_param} if year_param else {}
        result = await client.search(query_str, max_results=limit, **extra_params)
    else:
        raise SourceError(f"Unknown source: {source!r}.")

    papers = result.papers

    # --- Write to cache ---
    if not no_cache:
        cache.set(key, [json.loads(p.model_dump_json()) for p in papers], "search")

    return papers


async def _search_async(
    cfg: Config,
    raw_query: str,
    sources: list[str],
    limit: int,
    title: str | None,
    author: str | None,
    venue: str | None,
    year_from: int | None,
    year_to: int | None,
    sort: str,
    no_cache: bool,
) -> list[Paper]:
    """Async core: concurrent fetch → year-filter → dedup → rank → slice.

    Args:
        cfg: Resolved application config.
        raw_query: Raw user query string (may contain ``field:value`` tokens).
        sources: List of source names to query.
        limit: Maximum results to return after ranking.
        title: Optional title-filter keyword (from ``--title`` flag).
        author: Optional author-filter keyword (from ``--author`` flag).
        venue: Optional venue-filter keyword (from ``--venue`` flag).
        year_from: Optional lower year bound.
        year_to: Optional upper year bound.
        sort: Ranking criterion.
        no_cache: Bypass cache when True.

    Returns:
        Ranked, deduplicated list of up to *limit* papers.

    Raises:
        SourceError: If all sources fail.
        NoResultsError: If no results remain after dedup/filtering.
    """
    base_keywords, inline_filters = parse_query(raw_query)

    # Merge inline filters with explicit CLI flags (CLI flags win).
    if title:
        inline_filters["title"] = title
    if author:
        inline_filters["author"] = author
    if venue:
        inline_filters["venue"] = venue

    # Build per-source query strings.
    arxiv_q = build_arxiv_query(base_keywords, inline_filters)
    ss_q = build_ss_query(base_keywords, inline_filters)
    source_queries = {"arxiv": arxiv_q, "semantic_scholar": ss_q}

    cache_db = Cache(cfg.cache_dir / "cache.db")
    api_key = cfg.credentials.semantic_scholar_api_key

    # Fire off all sources concurrently, tolerating per-source failures.
    tasks = {
        source: _fetch_source(
            source=source,
            query_str=source_queries[source],
            limit=limit,
            sort=sort,
            year_from=year_from,
            year_to=year_to,
            cache=cache_db,
            no_cache=no_cache,
            api_key=api_key,
        )
        for source in sources
    }

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    all_papers: list[Paper] = []
    errors: list[SourceError] = []

    for source, result in zip(tasks.keys(), results, strict=True):
        if isinstance(result, SourceError):
            logger.warning("Source %s failed: %s", source, result.message)
            errors.append(result)
        elif isinstance(result, Exception):
            logger.warning("Source %s raised unexpected error: %s", source, result)
            errors.append(
                SourceError(
                    f"{source} raised an unexpected error: {result}",
                    suggestion="Run `lumen doctor` to check source connectivity.",
                )
            )
        else:
            all_papers.extend(result)

    if not all_papers and errors:
        # All sources failed — surface the first error.
        raise errors[0]

    # Post-filter by year (arXiv has no native year-range param).
    if year_from or year_to:
        all_papers = [
            p for p in all_papers if in_year_range(p.year, year_from, year_to)
        ]

    # Deduplicate, rank, slice.
    unique = deduplicate(all_papers)
    ranked = rank(unique, criterion=sort, query=base_keywords or raw_query)
    final = ranked[:limit]

    if not final:
        hint = "Try broader keywords or remove field filters." if inline_filters else ""
        raise NoResultsError("No results found.", suggestion=hint)

    return final
